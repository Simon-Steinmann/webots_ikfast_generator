
import os
import sys
import trimesh
import optparse
import multiprocessing
import xml.etree.ElementTree as ET
import xml.dom.minidom
import re
import rospkg
import signal
import gc
import shutil


def convert(inFile, outPath, name):
    meshes = trimesh.load(inFile)
    outFile = os.path.join(outPath, name) + '.obj'
    try:
        vhacd_mesh = trimesh.interfaces.vhacd.convex_decomposition(meshes,
            resolution=100000,
            pca=1, 
            #maxhulls=4, 
            #planeDownsampling=4, 
            #maxNumVerticesPerCH=32,
            #depth=8,
            #alpha=.9,
            gamme=0
            )
        scene = trimesh.scene.scene.split_scene(vhacd_mesh)
        trimesh.exchange.export.export_mesh(scene, outFile)
    except Exception as e:
        print(e)
    
    """    
    trimesh.exchange.export.export_mesh(meshes, outFile)
    p.connect(p.DIRECT)
    name_log = 'vacd_log.txt'
    p.vhacd(outFile, outFile, name_log, pca=0, convexhullDownsampling=4, planeDownsampling=4, maxNumVerticesPerCH=24)
    """    
    gc.collect()


def convert_all(pool, sourcePath, outPath=None, ext=None, recursive=True, replace=False):
    if ext is None:
        ext = ['.dae', '.stl', '.obj']
    print(sourcePath, outPath, ext)
    fileList = []
    if recursive:
        # find all files of in sourcepath that match the extension recursively
        for root, directories, files in os.walk(sourcePath):
            for filename in files:
                if os.path.splitext(filename)[1] in ext:
                    filepath = os.path.join(root, filename)
                    fileList.append(filepath)
    else:
        # find all files of in sourcepath that match the extension. Only in specified path.
        fileList = [f for f in os.listdir(sourcePath) if os.path.isfile(os.path.join(sourcePath, f))
                    and os.path.splitext(f)[1] in ext]
    for f in fileList:
        print(f"converting: {f}")
        name = os.path.splitext(f)[0]
        if ext == '.urdf':
            convert_from_urdf(pool, os.path.join(sourcePath, f), replace)
        else:
            # parse conversion job to process pool
            multiprocessing.active_children()
            pool.apply_async(convert, args=((os.path.join(sourcePath, f), outPath, name)))


def convert_from_urdf(pool, inFile, replace):
    os.chdir(os.path.dirname(inFile))
    inFile = os.path.abspath(inFile)
    endStr = '.urdf' if replace else '_optimized.urdf'
    if inFile.endswith('.urdf'):
        outFile = os.path.splitext(inFile)[0] + endStr
    tree = ET.parse(inFile)
    root = tree.getroot()
    parent_map = {c:  p for p in root.iter() for c in p}
    links = root.findall('.//link')
    for link in links:
        collMeshes = link.findall('./collision/geometry/mesh')
        for mesh in collMeshes:
            link.remove(parent_map[parent_map[mesh]])
        meshes = link.findall('./visual/geometry/mesh')
        for mesh in meshes:
            parentVisual = parent_map[parent_map[mesh]]
            path = mesh.attrib.get("filename")
            filePath = check_path(path)
            name = os.path.splitext(os.path.basename(path))[0]
            outfile = os.path.splitext(path)[0] + '.obj'
            col = ET.SubElement(link, 'collision')
            origin = parentVisual.find('origin')
            if origin is not None:
                orgn = ET.SubElement(col, 'origin')
                if origin.attrib.get('rpy') is not None:
                    orgn.set('rpy', origin.attrib.get('rpy'))
                if origin.attrib.get('xyz') is not None:
                    orgn.set('xyz', origin.attrib.get('xyz'))
            geo = ET.SubElement(col, 'geometry')
            m = ET.SubElement(geo, 'mesh', attrib={'filename': outfile})
            if mesh.attrib.get('scale') is not None:
                m.set('scale', mesh.attrib.get('scale'))
            # parse conversion job to process pool
            multiprocessing.active_children()
            pool.apply_async(convert, args=(filePath, os.path.dirname(filePath), name))

    xml_string = xml.dom.minidom.parseString(ET.tostring(root)).toprettyxml()
    xml_string = xml_string.replace("&quot;", '')
    xml_string = os.linesep.join([s for s in xml_string.splitlines() if s.strip()])
    with open(outFile, "w") as file_out:
        file_out.write(xml_string)


def check_path(path):
    """Try to get a valid filehandle to mesh file"""
    # This function is taken and adapted from
    # https://github.com/cyberbotics/urdf2webots/blob/master/urdf2webots/importer.py
    # credit goes to the team of https://cyberbotics.com/

    if os.path.exists(path):
        return os.path.abspath(path)
    else:
        package = re.findall('package://(.*)', path)
        if package:
            packageName = package[0].split('/')[0]
            directory = os.path.dirname(os.getcwd())
            while packageName != os.path.split(directory)[1] and os.path.split(directory)[1]:
                directory = os.path.dirname(directory)
            if not os.path.split(directory)[1]:
                try:
                    rospack = rospkg.RosPack()
                    directory = rospack.get_path(packageName)
                except rospkg.common.ResourceNotFound:
                    sys.stderr.write('Package "%s" not found.\n' % packageName)
                except NameError:
                    sys.stderr.write('Impossible to find location of "%s" package, installing "rospkg" might help.\n'
                                     % packageName)
            if os.path.split(directory)[1]:
                packagePath = os.path.split(directory)[0]
                path = path.replace('package:/', packagePath)
            else:
                sys.stderr.write('Can\'t determine package root path.\n')
        else:
            rootDir = path.split('/')[0]
            directory = os.path.dirname(os.getcwd())
            while rootDir != os.path.split(directory)[1] and os.path.split(directory)[1]:
                directory = os.path.dirname(directory)
            if os.path.split(directory)[1]:
                path = os.path.join(os.path.dirname(directory), path)
            else:
                sys.stderr.write('Can\'t determine mesh location!\n')
        return path


def create_backup(sourcePath):
    # Create a backup of the folder we are converting
    backupName = os.path.basename(sourcePath) + '_backup_0'
    backupPath = os.path.join(os.getcwd(), backupName)
    n = 0
    while os.path.isdir(backupPath):
        n += 1
        backupPath = backupPath[:-1] + str(n)
    shutil.copytree(sourcePath,  backupPath)


def initializer():
    """Ignore CTRL+C in the worker process."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


if __name__ == "__main__":
    optParser = optparse.OptionParser(usage='usage: %prog  [options]')
    optParser.add_option('--input', dest='inPath', default=None,
                         help='Specifies the proto file, or a directory. Converts all .proto files, if it is a directory.')
    optParser.add_option('--outPath', dest='outPath', default=None, help='Where converted obj file should be placed.')
    optParser.add_option('--type', dest='ext', default=None, help='The file extensions of the meshes we want to convert. '
                         'can be list [".dae", ".obj"]')
    optParser.add_option('--replace', dest='replace', action='store_true', default=False, help='If set, will replace .urdf '
                         ' files instead of creating a new "<filename>_optimized.urdf". This will turn the --backup option '
                         ' on.')
    optParser.add_option('--backup', dest='backup', action='store_true', default=False, help='If set, will create a backup '
                         ' of the "--input" in your current working directory.')
    options, args = optParser.parse_args()

    inPath = options.inPath
    outPath = options.outPath
    if options.backup or options.replace:
        create_backup(inPath)

    core_count = multiprocessing.cpu_count()
    print('CPU core count: ', core_count)
    # use all available cores, otherwise specify the number you want as an argument
    pool = multiprocessing.Pool(core_count, initializer=initializer, maxtasksperchild=10)

    if inPath is None:
        sys.exit('No input! set with --input=<path>')
    if outPath is None:
        outPath = inPath
    ext = os.path.splitext(inPath)[1]
    print(options.ext, ext)
    try:
        if ext == '.urdf':
            convert_from_urdf(pool, inPath, replace=options.replace)
        elif os.path.isfile(inPath):
            if ext not in ['.stl', '.dae', '.obj']:
                sys.exit(" --input=<path> either needs to be a directory or a file of type: ['.stl', '.dae', '.obj', '.urdf']")
            else:
                name = os.path.splitext(os.path.basename(inPath))[0]
                convert(inPath, outPath, name)
        else:
            convert_all(pool, inPath, outPath, ext=options.ext, replace=options.replace)
        pool.close()
        pool.join()
        print('-----------------------------------------------------------------')
        print('Collision mesh optimization complete. Script by Simon-Steinmann (https://github.com/Simon-Steinmann)')
    except KeyboardInterrupt:
        print('-----------------------------------------------------------------')
        pool.terminate()
        pool.join()
        sys.exit("KeyboardInterrupt! Terminating running processes.")
