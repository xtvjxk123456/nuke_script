# coding:utf-8
import xml.etree.ElementTree as ET
from Qt import QtWidgets, QtGui, QtCore


def _getUI(element):
    if element.tag not in {"Menu", "Action", "Separator"}:
        return None
    if element.tag == "Menu":
        m = QtWidgets.QMenu(element.attrib.get("label", ""))
        return m
    if element.tag == "Action":
        a = QtWidgets.QAction(element.attrib.get("label", ""))
        return a
    if element.tag == "Separator":
        s = QtWidgets.QAction()
        s.setSeparator(True)
        return s


def _modifyMenu(element, menu):
    for child in element.getchildren():
        if child.tag not in {"Menu", "Action", "Separator"}:
            continue
        if child.tag == "Action":
            action = _getUI(child)
            menu.addAction(action)
        if child.tag == "Separator":
            action = _getUI(child)
            menu.addAction(action)
        if child.tag == "Menu":
            subMenu = _getUI(child)
            menu.addMenu(subMenu)
            _modifyMenu(child, subMenu)


def createUiFromXml(xmlpath):
    try:
        tree = ET.parse(xmlpath)
    except Exception:
        return None
    root = tree.getroot()
    if root.tag not in {"Menu", "MenuBar"}:
        # 为menu.xml,意图支持单menu和多menu
        return None
    menu = _getUI(root)
    _modifyMenu(root, menu)
    return menu
