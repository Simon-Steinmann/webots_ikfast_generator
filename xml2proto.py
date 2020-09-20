
import xml.etree.ElementTree as ET
import xml.dom.minidom
import os
import trimesh
import optparse
import numpy as np
from transforms3d import euler


def getMesh(vertex_index, coord):
    #print(coordIndex)    
    coord = list(map(float,coord))
    #print(len(vertex_index), len(coord))
    vertex = np.array(coord).reshape(-1,3)
    vertices = vertex[vertex_index]
    faces = np.arange(
        vertices.shape[0]).reshape(
        vertices.shape[0] // 3, 3)
    #color = np.array([255, 0, 0], dtype='uint8')
    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
    return mesh

class xml2urdf():
    def __init__(self, robotName, urlPrefix):
        self.robotName = robotName
        self.urlPrefix = urlPrefix
        self.urdfTree = ET.ElementTree(ET.Element('robot', attrib={'name': robotName}))
        self.urdfRoot = self.urdfTree.getroot()
        self.elemList = [self.urdfRoot]
        self.tree = ET.parse('export/{}/{}.xml'.format(self.robotName, self.robotName))
        self.root = self.tree.getroot()
        self.parent_map = {c:p for p in self.root.iter( ) for c in p}

    def convert(self):
        self.chain = self.root.findall('.//Solid')
        print(self.chain, len(self.chain))        
        self.root.tag = 'Solid'
        self.root.set('name', 'base_link')
        self.createLink(self.root)
        for solid in self.chain:
            parent = self.parent_map[solid]
            self.createLink(solid)
            if parent.tag == 'HingeJoint':            
                self.createJoint(solid, parent)
            else:
                self.createFixedJoint(solid, parent)            
        self.urdfTree.write('export/test.urdf') 
        self.pretty_print_xml_given_root(self.urdfRoot, 'export/{}/{}.urdf'.format(self.robotName, self.robotName))

    def createLinkMesh(self, solid):
        linkname = solid.get('name')
        try:
            shapes = solid.find('children').findall('Shape')                          
        except:
            return False  
        for child in solid.find('children'):
            if child.tag != 'Solid':
                use = child.attrib.get('USE')
                if use is not None:
                    child = self.root.findall('.//*[@DEF="' + use+ '"]')[0]  
                children = child.find('children')
                if children is not None:
                    for elem in children:
                        if elem.tag == 'Shape':                            
                            shapes.append(elem)  
        trimeshes = []
        for shape in shapes:
            meshes = shape.findall('.//geometry[@type="IndexedFaceSet"]')
            cylinders = shape.findall('.//geometry[@type="Cylinder"]')
            for c in cylinders:
                r = c.attrib.get('radius')
                h = c.attrib.get('height')
                print(trimesh.primitives.Cylinder(radius=r, height=h).segment)
            if len(meshes) == 0:
                continue            
            for mesh in meshes:
                attrib = mesh.attrib.get('USE')
                if attrib is not None:
                    searchString = ".//geometry[@DEF='{}']".format(attrib)
                    mesh = self.root.find(searchString)
                coordIndex = mesh.attrib.get(('coordIndex')).split(',')
                coord = ' '.join(mesh.find('coord').attrib.get(('point')).split(',')).split()
                try:
                    vertex_index = np.array(coordIndex, dtype=int).reshape(-1,4)[:,:3].flatten()
                except:
                    print('Warning: coordIndex has the wrong format!')
                    continue
                trimeshes.append(getMesh(vertex_index, coord))
        #print(trimeshes)
        if len(trimeshes) != 0:            
            union = trimesh.boolean.union(trimeshes) 
            convexHull = trimesh.convex.convex_hull(union)
            trimesh.exchange.export.export_mesh(convexHull, 'export/' + self.robotName + '/meshes/collision/{}.stl'.format(linkname))   
            trimesh.exchange.export.export_mesh(trimeshes, 'export/' + self.robotName + '/meshes/visual/{}.dae'.format(linkname))
            return True
        else:
            return False

    def createLink(self, solid):
        hasMesh = self.createLinkMesh(solid)
        self.elemList.append(ET.SubElement(self.urdfRoot, 'link'))
        origin = None
        if solid == self.root:
            linkname = 'base_link'
        else:
            try:
                linkname = '_'.join(solid.attrib.get('name').split())
            except:
                linkname = 'link_' + str(self.chain.index(solid))
            parent_joint = self.parent_map[solid].find('.//jointParameters')
            #print(parent_joint)
            if parent_joint is not None:
                if parent_joint.attrib.get('anchor') is not None:
                    origin1 = np.array(list(map(float, parent_joint.attrib.get('anchor').split())))
                else:
                    origin1 = np.array([0, 0, 0])
                if solid.attrib.get('translation') is not None:
                    origin2 =  np.array(list(map(float, solid.attrib.get('translation').split())))
                else:
                    origin2 = np.array([0, 0, 0])
                origin = origin2 - origin1
                origin = ' '.join(map(str, np.round(origin,6)))                
        self.elemList[-1].set('name', linkname)
        print('Creating LINK: {} and extracting meshes'.format(linkname))
        if hasMesh:
            visual = ET.SubElement(self.elemList[-1], 'visual')
            if origin is not None:
                ET.SubElement(visual, 'origin',  attrib={'xyz': origin})   
            geometry = ET.SubElement(visual, 'geometry')
            ET.SubElement(geometry, 'mesh',  attrib={'filename': '{}/meshes/visual/{}.dae'.format(self.urlPrefix, linkname)})
            collision = ET.SubElement(self.elemList[-1], 'collision')
            if origin is not None:
                ET.SubElement(collision, 'origin',  attrib={'xyz': origin})  
            geometry = ET.SubElement(collision, 'geometry')
            ET.SubElement(geometry, 'mesh',  attrib={'filename': '{}/meshes/collision/{}.stl'.format(self.urlPrefix, linkname)})


    def createJoint(self, solid, parent):
        jParam = parent.find('.//jointParameters')
        motor = parent.find('.//RotationalMotor')
        parent_link = parent
        anchor = jParam.attrib.get('anchor')
        if anchor is not None:
            origin = np.array(list(map(float, anchor.split())))
        else:
            origin = np.array([0, 0, 0])
        while parent_link.tag != 'Solid':
            parent_link = self.parent_map[parent_link]
        if parent_link != self.root:
            parent_joint = self.parent_map[parent_link].find('.//jointParameters')
            if parent_joint is not None:
                if parent_joint.attrib.get('anchor') is not None:
                    origin2 = np.array(list(map(float, parent_joint.attrib.get('anchor').split())))
                else:
                    origin2 = np.array([0, 0, 0])
                if parent_link.attrib.get('translation') is not None:
                    origin3 =  np.array(list(map(float, parent_link.attrib.get('translation').split())))
                else:
                    origin3 = np.array([0, 0, 0])
                origin = origin - origin2 + origin3
        origin = ' '.join(map(str, np.round(origin,6)))
        self.elemList.append(ET.SubElement(self.urdfRoot, 'joint'))        
        self.elemList[-1].set('type', 'revolute')
        originElem = ET.SubElement(self.elemList[-1], 'origin',  attrib={'xyz': origin})
        try:
            linkname = '_'.join(parent_link.get('name').split())
        except:
            linkname = 'link_' + str(self.chain.index(parent_link))
        ET.SubElement(self.elemList[-1], 'parent',  attrib={'link': linkname })
        try:
            childname = '_'.join(solid.attrib.get('name').split())
        except:
            childname = 'link_' + str(self.chain.index(solid))
        ET.SubElement(self.elemList[-1], 'child',  attrib={'link':  linkname})
        try:
            name = '_'.join(motor.attrib.get('name').split())
        except:
            name ='joint_' + linkname + '_' + childname
        self.elemList[-1].set('name', name)
        axis = jParam.attrib.get('axis')
        ET.SubElement(self.elemList[-1], 'axis',  attrib={'xyz': axis if axis is not None else '1 0 0'})
        try:
            limit = ET.SubElement(self.elemList[-1], 'limit')
            limitList = [motor.attrib.get('maxTorque'), motor.attrib.get('minPosition'), motor.attrib.get('maxPosition'), motor.attrib.get('maxVelocity')]
            limitTypes = ['effort', 'lower', 'upper', 'velocity']
            for i in range(4):
                if limitList[i] is not None:
                    limit.set(limitTypes[i], limitList[i])
        except:
            print('no limits')
        rotation = solid.attrib.get('rotation')
        if rotation is not None:
            rotation = np.array(list(map(float, rotation.split())))
            rpy = euler.axangle2euler(rotation[:3],rotation[3])
            originElem.set('rpy', ' '.join(map(str, rpy)))


    def createFixedJoint(self, solid, parent):
        parent_link = parent
        while parent_link.tag != 'Solid':
            parent_link = self.parent_map[parent_link]
        self.elemList.append(ET.SubElement(self.urdfRoot, 'joint'))
        try:
            name = '_'.join(solid.attrib.get('name').split())
        except:
            name = 'link_' + str(self.chain.index(solid))
        try:
            parentName = '_'.join(parent_link.attrib.get('name').split())
        except:
            parentName = 'link_' + str(self.chain.index(parent_link))
        self.elemList[-1].set('name', 'joint_{}_{}'.format(name, parentName))
        self.elemList[-1].set('type', 'fixed')
        ET.SubElement(self.elemList[-1], 'origin',  attrib={'xyz': solid.attrib.get('translation')})
        ET.SubElement(self.elemList[-1], 'parent',  attrib={'link':  parentName})
        ET.SubElement(self.elemList[-1], 'child',  attrib={'link': name})

    def pretty_print_xml_given_root(self, root, output_xml):
        """
        Useful for when you are editing xml data on the fly
        """
        xml_string = xml.dom.minidom.parseString(ET.tostring(root)).toprettyxml()
        xml_string = os.linesep.join([s for s in xml_string.splitlines() if s.strip()]) # remove the weird newline issue
        with open(output_xml, "w") as file_out:
            file_out.write(xml_string)  

if __name__ == "__main__":
    optParser = optparse.OptionParser(usage='usage: %prog  [options]')
    optParser.add_option('--name', dest='robotName', default='', help='Specifies the robotName.')
    optParser.add_option('--ikfast', dest='ikfast', action='store_true', default=False,
                         help='If set, changes the urdf-mesh urls absolute for ikfast-solver generation')
    options, args = optParser.parse_args()

    robotName = options.robotName
    #path =  os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists('export/' + robotName + '/meshes/visual'):
        os.makedirs('export/' + robotName + '/meshes/visual')
    if not os.path.exists('export/' + robotName + '/meshes/collision'):
        os.makedirs('export/' + robotName + '/meshes/collision')
    if options.ikfast:
        urlPrefix = 'file:///home/' + robotName
    else:
        urlPrefix = '.'
    xml2urdf = xml2urdf(robotName, urlPrefix)
    xml2urdf.convert()
