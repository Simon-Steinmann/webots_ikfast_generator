
import xml.etree.ElementTree as ET
import os
import optparse
import numpy as np

import xml.dom.minidom


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
    ln = f.readline().split()
    while not '{' in ln:
        ln = f.readline().split()
    tree = ET.ElementTree(ET.Element(ln[0]))
    root = tree.getroot()
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
                #tree.write('export/proto.xml') 
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
                    elemList[-1].set('type', ln[-2])           
                elemList[-1].set('DEF', ln[i + 1])
            if 'USE' in ln:
                elemList[-1].set('type', ln[-2])           
                elemList[-1].set('USE', ln[ln.index('USE') + 1])
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
            elemList[-1].set(attribute, data)
        elif len(ln) > 1:
            if ln[0] == 'USE':
                node = root.findall('.//*[@DEF="' + ln[1] + '"]')[0]          
                elemList.append(ET.SubElement(elemList[hierarchy[-1]], node.tag))
                elemList[-1].set('USE', ln[1])
            else:    
                elemList[-1].set(ln[0],  ' '.join(ln[1:]))  
            
                    
       


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
