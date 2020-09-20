
import xml.etree.ElementTree as ET
import os
import optparse
import numpy as np

import xml.dom.minidom

HingeJointParametersDefaults = {
  'anchor': '0 0 0',   # any vector
  'axis': '1 0 0',   # unit axis
  'suspensionSpringConstant': '0', # [0, inf)
  'suspensionDampingConstant': '0',      # [0, inf)
  'suspensionAxis': '1 0 0',  # unit axis
}
SolidDefaults = {
    'translation': '0 0 0',
    'rotation': '0 1 0 0'}

def add_defaults(root):
    i = 0
    for node in root.findall('.//'):
        i += 1
        if node.tag == 'HingeJointParameters':
            for k, v in HingeJointParametersDefaults.items():
                if node.attrib.get(k) is None:
                    node.set(k, v)
        if node.tag in ['Solid', 'Transform', 'Group']:
            for k, v in SolidDefaults.items():
                if node.attrib.get(k) is None:
                    node.set(k, v)
            name = node.attrib.get('name')
            if name is None:
                name = 'link'
            name = name.replace('(', '_').replace(')', '_')  + '_' + str(i)
            node.set('name', name)
    return root
    

    

def pretty_print_xml_given_root(root, output_xml):
    """
    Useful for when you are editing xml data on the fly
    """
    xml_string = xml.dom.minidom.parseString(ET.tostring(root)).toprettyxml()
    xml_string = xml_string.replace("&quot;",'')
    xml_string = os.linesep.join([s for s in xml_string.splitlines() if s.strip()]) # remove the weird newline issue
    with open(output_xml, "w") as file_out:
        file_out.write(xml_string)

def pretty_print_xml_given_file(input_xml, output_xml):
    """
    Useful for when you want to reformat an already existing xml file
    """
    tree = ET.parse(input_xml)
    root = tree.getroot()
    pretty_print_xml_given_root(root, output_xml)

def proto2xml(f, robotName):
    level = 0
    #ln = f.readline().split()
    while True:
        ln = f.readline().split()
        if '{' in ln:
            tree = ET.ElementTree(ET.Element(ln[0]))
            root = tree.getroot()
            break
        if '[' in ln:
            tree = ET.ElementTree(ET.Element(ln[1]))
            root = tree.getroot()
            root.set('type', ln[0])
            line = f.readline()
            ln = line.split()
            while not ']' in ln:                
                #print(ln[2], ' '.join(ln[3:]).split('#')[0])
                field = ET.SubElement(root, ln[0], attrib={'type': ln[1]})
                fdata = ' '.join(ln[3:]).split('#')[0].split()
                field.set(ln[2], ' '.join(fdata))
                field.set('comment', line.split('#')[1])
                print(line.split('#')[1])
                line = f.readline()
                ln = line.split()
            ln = f.readline().split()
            break
            


    #print(xml.dom.minidom.parseString(ET.tostring(root)).toprettyxml())
    elemList = [root]
    hierarchy = [0]
    indent = '  '
    index = 1
    while True:   
        ln = f.readline().split()  # python3
        # termination condition:
        eof = 0
        while ln == []:
            ln = f.readline().split()
            eof += 1
            if eof > 10:
                print('done parsing')
                tree.write('export/proto.xml') 
                root = add_defaults(root)
                pretty_print_xml_given_root(root, 'export/{}/{}.xml'.format(robotName, robotName))
                return     
        if '{' in ln or 'children' in ln or 'device' in ln:          
            elemList.append(ET.SubElement(elemList[hierarchy[-1]], ln[0]))
            if len(ln) == 3:
                elemList[-1].set('type', ln[1])
            if 'endPoint' in ln:
                i = ln.index('endPoint')
                if i == 0:
                    elemList[-1].tag = ln[-2]
                    elemList[-1].set('type', 'endPoint')                    
            if 'DEF' in ln:
                i = ln.index('DEF')
                if i == 0:
                    elemList[-1].tag = ln[-2]
                else:
                    if elemList[-1].attrib.get('type') != 'endPoint':
                        elemList[-1].set('type', ln[-2])           
                elemList[-1].set('DEF', ln[i + 1])
            if 'USE' in ln:
                elemList[-1].set('type', ln[-2])           
                elemList[-1].set('USE', ln[ln.index('USE') + 1])
            if 'IS' in ln:
                elemList[-1].set('IS', ln[ln.index('IS') + 1])
            else:
                hierarchy.append(len(elemList) - 1)
        elif '}' in ln or ']' in ln:
            del hierarchy[-1]
        elif '[' in ln:
            attribute = ln[0]
            ln = f.readline().split()
            data = ""
            while not ']' in ln:                    
                data += ' ' + ' '.join(ln)
                ln = f.readline().split()
            elemList[-1].set(attribute, data[:10])
        elif '%{' in ln:
            print(' '.join(ln))
            elemList.append(ET.SubElement(elemList[hierarchy[-1]], 'script'))
            print(elemList[-1], elemList[hierarchy[-1]])
            elemList[-1].set('code', ' '.join(ln))
        elif len(ln) > 1:
            if ln[0] == 'USE':
                node = root.findall('.//*[@DEF="' + ln[1] + '"]')[0]          
                elemList.append(ET.SubElement(elemList[hierarchy[-1]], node.tag))
                elemList[-1].set('USE', ln[1])
            else:
                print(elemList[-1], elemList[hierarchy[-1]])
                elemList[hierarchy[-1]].set(ln[0],  ' '.join(ln[1:]))  
            
                    
       


if __name__ == "__main__":
    optParser = optparse.OptionParser(usage='usage: %prog  [options]')
    optParser.add_option('--name', dest='robotName', default='', help='Specifies the robotName.')
    options, args = optParser.parse_args()

    robotName = options.robotName
    if not os.path.exists('export/' + robotName + '/'):
        os.makedirs('export/' + robotName + '/')
    if not os.path.exists('export/' + robotName + '/'):
        os.makedirs('export/' + robotName + '/')
    f=open('import/{}.proto'.format(robotName))
    proto2xml(f, robotName)
