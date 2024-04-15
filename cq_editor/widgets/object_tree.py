from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QAction, QMenu, QWidget, QAbstractItemView, QHeaderView
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from pyqtgraph.parametertree import Parameter, ParameterTree

from OCP.AIS import AIS_Line
from OCP.Geom import Geom_Line
from OCP.gp import gp_Dir, gp_Pnt, gp_Ax1

from ..mixins import ComponentMixin
from ..icons import icon
from ..cq_utils import make_AIS, export, to_occ_color, is_obj_empty, get_occ_color, set_color
from .viewer import DEFAULT_FACE_COLOR
from ..utils import splitter, layout, get_save_filename

class GroupTreeItem(QTreeWidgetItem):
    props = [{'name': 'Visible', 'type': 'bool','value': True}]
    def __init__(self,name,sig,*args,**kwargs):

        super(GroupTreeItem,self).__init__(name, *args,**kwargs)
        self.setFlags( self.flags() | Qt.ItemIsUserCheckable)
        self.setCheckState(1,Qt.Checked)

        self.sig = sig

        self.properties = Parameter.create(name='Properties', children=self.props)
        self.properties.sigTreeStateChanged.connect(self.propertiesChanged)
        self.propertiesChanged(self.properties,[[self.properties['Visible']]])

    def propertiesChanged(self, properties, changed):        
        if self.properties['Visible']:
            self.setCheckState(1,Qt.Checked)
        else:
            self.setCheckState(1,Qt.Unchecked)

        if self.sig:
            self.sig.emit()

class ObjectTreeItem(QTreeWidgetItem):

    props = [{'name': 'Name', 'type': 'str', 'value': ''},
             {'name': 'Color', 'type': 'color', 'value': "#f4a824"},
             {'name': 'Alpha', 'type': 'float', 'value': 0, 'limits': (0,1), 'step': 1e-1},
             {'name': 'Visible', 'type': 'bool','value': True}]

    def __init__(self,
                 name,
                 ais=None,
                 label_ais=None,
                 shape=None,
                 shape_display=None,
                 sig=None,
                 alpha=0.,
                 color='#f4a824',
                 **kwargs):

        super(ObjectTreeItem,self).__init__([name],**kwargs)
        self.setFlags( self.flags() | Qt.ItemIsUserCheckable)
        self.setCheckState(1,Qt.Checked)

        self.ais = ais
        self.label_ais = label_ais
        self.shape = shape
        self.shape_display = shape_display
        self.sig = sig

        self.properties = Parameter.create(name='Properties',
                                           children=self.props)

        self.properties['Name'] = name
        self.properties['Alpha'] = ais.Transparency()
        self.properties['Visible'] = True
        self.properties['Color'] = get_occ_color(ais) if ais and ais.HasColor() else get_occ_color(DEFAULT_FACE_COLOR)
        self.properties.sigTreeStateChanged.connect(self.propertiesChanged)

        # trigger propertiesChanged to set initial values
        self.propertiesChanged(self.properties,[[self.properties['Visible']]])

    def propertiesChanged(self, properties, changed):

        changed_prop = changed[0][0]

        self.setData(0,0,self.properties['Name'])
        self.ais.SetTransparency(self.properties['Alpha'])

        try:
            if changed_prop.name() == 'Color':
                set_color(self.ais, to_occ_color(self.properties['Color']))
        
            self.ais.Redisplay()
        except AttributeError:
            pass

        if self.properties['Visible']:
            self.setCheckState(1,Qt.Checked)
        else:
            self.setCheckState(1,Qt.Unchecked)

        if self.sig:
            self.sig.emit()

class CQRootItem(GroupTreeItem):

    def __init__(self,sig):

        super(CQRootItem,self).__init__(name=['Models'], sig=sig)


class HelpersRootItem(GroupTreeItem):

    def __init__(self,sig):

        super(HelpersRootItem,self).__init__(name=['Helpers'],sig=sig)


class ObjectTree(QWidget,ComponentMixin):

    name = 'Object Tree'
    _stash = []

    preferences = Parameter.create(name='Preferences',children=[
        {'name': 'Preserve properties on reload', 'type': 'bool', 'value': False},
        {'name': 'Clear all before each run', 'type': 'bool', 'value': True},
        {'name': 'STL precision','type': 'float', 'value': .1}])

    sigObjectsAdded = pyqtSignal([list],[list,bool])
    sigObjectsRemoved = pyqtSignal(list)
    sigCQObjectSelected = pyqtSignal(object)
    sigAISObjectsSelected = pyqtSignal(list)
    sigItemChanged = pyqtSignal(QTreeWidgetItem,int)
    sigObjectPropertiesChanged = pyqtSignal()

    def  __init__(self,parent):

        super(ObjectTree,self).__init__(parent)

        self.tree = tree = QTreeWidget(self, selectionMode=QAbstractItemView.ExtendedSelection)
        self.properties_editor = ParameterTree(self)

        tree.setHeaderHidden(True)
        tree.setColumnCount(2)

        # tree.setItemsExpandable(False)
        tree.setRootIsDecorated(False)
        tree.setContextMenuPolicy(Qt.ActionsContextMenu)

        #forward itemChanged singal
        tree.itemChanged.connect(lambda item,col: self.sigItemChanged.emit(item,col))
        #handle visibility changes form tree
        tree.itemChanged.connect(self.handleChecked)

        self.CQ = CQRootItem(sig=self.sigObjectPropertiesChanged)
        self.Helpers = HelpersRootItem(sig=self.sigObjectPropertiesChanged)

        root = tree.invisibleRootItem()
        root.addChild(self.CQ)
        root.addChild(self.Helpers)
        
        tree.expandToDepth(1)

        tree.header().setStretchLastSection(False)
        tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)

        self._export_STL_action = \
            QAction('Export as STL',
                    self,
                    enabled=False,
                    triggered=lambda: \
                        self.export('stl',
                                    self.preferences['STL precision']))

        self._export_STEP_action = \
            QAction('Export as STEP',
                    self,
                    enabled=False,
                    triggered=lambda: \
                        self.export('step'))

        self._clear_current_action = QAction(icon('delete'),
                                             'Clear current',
                                             self,
                                             enabled=False,
                                             triggered=self.removeSelected)

        self._toolbar_actions = \
            [QAction(icon('delete-many'),'Clear all',self,triggered=self.removeObjects),
             self._clear_current_action,]

        self.prepareMenu()

        tree.itemClicked.connect(self.handleClick)
        tree.itemSelectionChanged.connect(self.handleSelection)
        tree.customContextMenuRequested.connect(self.showMenu)

        self.prepareLayout()


    def prepareMenu(self):

        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)

        self._context_menu = QMenu(self)
        self._context_menu.addActions(self._toolbar_actions)
        self._context_menu.addActions((self._export_STL_action,
                                       self._export_STEP_action))

    def prepareLayout(self):

        self._splitter = splitter((self.tree,self.properties_editor),
                                  stretch_factors = (2,1),
                                  orientation=Qt.Vertical)
        layout(self,(self._splitter,),top_widget=self)

        self._splitter.show()

    def showMenu(self,position):

        self._context_menu.exec_(self.tree.viewport().mapToGlobal(position))


    def menuActions(self):

        return {'Tools' : [self._export_STL_action,
                           self._export_STEP_action]}

    def toolbarActions(self):

        return self._toolbar_actions

    def addLines(self):

        origin = (0,0,0)
        ais_list = []

        for name,color,direction in zip(('X','Y','Z'),
                                        ('red','lawngreen','blue'),
                                        ((1,0,0),(0,1,0),(0,0,1))):
            line_placement = Geom_Line(gp_Ax1(gp_Pnt(*origin),
                                       gp_Dir(*direction)))
            line = AIS_Line(line_placement)
            line.SetColor(to_occ_color(color))
            
            self.Helpers.addChild(ObjectTreeItem(name,
                                                 ais=line))

            ais_list.append(line)

        self.sigObjectsAdded.emit(ais_list)

    def _current_properties(self):

        current_params = {}
        for i in range(self.CQ.childCount()):
            child = self.CQ.child(i)
            current_params[child.properties['Name']] = child.properties

        return current_params

    def _restore_properties(self,obj,properties):

        for p in properties[obj.properties['Name']]:
            obj.properties[p.name()] = p.value()

    @pyqtSlot(dict,bool)
    @pyqtSlot(dict)
    def addObjects(self,objects,clean=False,root=None):

        if root is None:
            root = self.CQ

        request_fit_view = True if root.childCount() == 0 else False
        preserve_props = self.preferences['Preserve properties on reload']
        
        if preserve_props:
            current_props = self._current_properties()

        if clean or self.preferences['Clear all before each run']:
            self.removeObjects()

        ais_list = []

        #remove empty objects
        objects_f = {k:v for k,v in objects.items() if not is_obj_empty(v.shape)}

        for path,obj in objects_f.items():
            parts = [p for p in path.split('/') if len(p) > 0]
            name = parts[-1]
            parts = [f"{p}/" for p in parts[:-1]]
            cur_level = root
            for part in parts:
                children = [cur_level.child(i) for i in range(cur_level.childCount())]
                if part not in [ch.text(0) for ch in children]:
                    group = GroupTreeItem([part],sig=self.sigObjectPropertiesChanged)
                    cur_level.addChild(group)

                cur_level = [cur_level.child(i) for i in range(cur_level.childCount()) if cur_level.child(i).text(0) == part][0]

            ais,shape_display,label_ais = make_AIS(obj.shape,obj.options)
            
            child = ObjectTreeItem(name,
                                   shape=obj.shape,
                                   shape_display=shape_display,
                                   ais=ais,
                                   label_ais=label_ais,
                                   sig=self.sigObjectPropertiesChanged)
            
            if preserve_props and name in current_props:
                self._restore_properties(child,current_props)
            
            if child.properties['Visible']:
                ais_list.append(ais)
                ais_list.append(label_ais)
            
            cur_level.addChild(child)

        if request_fit_view:
            self.sigObjectsAdded[list,bool].emit(ais_list,True)
        else:
            self.sigObjectsAdded[list].emit(ais_list)

    @pyqtSlot(object,str,object)
    def addObject(self,obj,name='',options={}):

        root = self.CQ

        ais,shape_display,label = make_AIS(obj, options)

        root.addChild(ObjectTreeItem(name,
                                     shape=obj,
                                     shape_display=shape_display,
                                     ais=ais,
                                     sig=self.sigObjectPropertiesChanged))

        self.sigObjectsAdded.emit([ais])

    @pyqtSlot(list)
    @pyqtSlot()
    def removeObjects(self,objects=None): #please !work!!!
        # if objects:
        #     removed_items_ais = [self.CQ.takeChild(i).ais for i in objects if hasattr(self.CQ.takeChild(i), "ais")]
        # else:
        #     removed_items_ais = [ch.ais for ch in self.CQ.takeChildren() if hasattr(ch, "ais")]

        # remove selected objects recursively
        removed_items_ais = []
        def remove_children(item):
            for i in range(item.childCount()):
                child = item.child(i)
                if hasattr(child, "ais"):
                    removed_items_ais.append(child.ais)
                if hasattr(child, "label_ais"):
                    removed_items_ais.append(child.label_ais)
                remove_children(child)
            
            for i in range(item.childCount()):
                item.takeChild(0)

        if objects:
            for i in objects:
                item = self.CQ.child(i)
                if hasattr(item, "ais"):
                    removed_items_ais.append(item.ais)
                if hasattr(item, "label_ais"):
                    removed_items_ais.append(item.label_ais)
                remove_children(item)
        else:
            remove_children(self.CQ)
            
        self.sigObjectsRemoved.emit(removed_items_ais)

    @pyqtSlot(bool)
    def stashObjects(self,action : bool):

        if action:
            self._stash = self.CQ.takeChildren()
            removed_items_ais = [ch.ais for ch in self._stash if hasattr(ch, "ais")]
            self.sigObjectsRemoved.emit(removed_items_ais)
        else:
            self.removeObjects()
            self.CQ.addChildren(self._stash)
            ais_list = [el.ais for el in self._stash if hasattr(el, "ais")]
            self.sigObjectsAdded.emit(ais_list)

    @pyqtSlot()
    def removeSelected(self):

        ixs = self.tree.selectedIndexes()
        rows = [ix.row() for ix in ixs]

        self.removeObjects(rows)

    def export(self,export_type,precision=None):

        items = self.tree.selectedItems()

        # if CQ models is selected get all children
        if [item for item in items if item is self.CQ]:
            CQ = self.CQ
            shapes = [CQ.child(i).shape for i in range(CQ.childCount()) if hasattr(CQ.child(i), "shape")]
        # otherwise collect all selected children of CQ
        else:
            shapes = [item.shape for item in items if hasattr(item, "shape")]

        fname = get_save_filename(export_type)
        if fname != '':
             export(shapes,export_type,fname,precision)

    def handleClick(self,item,col):
        if col == 0:
            if item.isExpanded():
                self.tree.collapseItem(item)
            else:
                self.tree.expandItem(item)
            
    @pyqtSlot()
    def handleSelection(self):

        items =self.tree.selectedItems()
        if len(items) == 0:
            self._export_STL_action.setEnabled(False)
            self._export_STEP_action.setEnabled(False)
            return

        # emit list of all selected ais objects (might be empty)
        ais_objects = [item.ais for item in items if item.parent() is self.CQ and hasattr(item, "ais")]
        self.sigAISObjectsSelected.emit(ais_objects)

        # handle context menu and emit last selected CQ  object (if present)
        item = items[-1]
        if hasattr(item,'shape'):
            self._export_STL_action.setEnabled(True)
            self._export_STEP_action.setEnabled(True)
            self._clear_current_action.setEnabled(True)
            self.sigCQObjectSelected.emit(item.shape)
            self.properties_editor.setParameters(item.properties, showTop=False)
            self.properties_editor.setEnabled(True)
        elif item.childCount() > 0:
            self._export_STL_action.setEnabled(True)
            self._export_STEP_action.setEnabled(True)

            self.properties_editor.setEnabled(False)
            self.properties_editor.clear()
        else:
            self._export_STL_action.setEnabled(False)
            self._export_STEP_action.setEnabled(False)
            self._clear_current_action.setEnabled(False)
            self.properties_editor.setEnabled(False)
            self.properties_editor.clear()

    @pyqtSlot(list)
    def handleGraphicalSelection(self,shapes):
        pass
        # self.tree.clearSelection()

        # CQ = self.CQ
        # for i in range(CQ.childCount()):
        #     item = CQ.child(i)
        #     for shape in shapes:
        #         if not hasattr(item, "shape"):
        #             continue

        #         if item.ais.Shape().IsEqual(shape):
        #             item.setSelected(True)

    @pyqtSlot(QTreeWidgetItem,int)
    def handleChecked(self,item,col):

        if type(item) is ObjectTreeItem:
            if item.checkState(1):
                item.properties['Visible'] = True
            else:
                item.properties['Visible'] = False
        else:
            # for i in range(item.childCount()):
            #     child = item.child(i)
            #     child.properties['Visible'] = item.properties['Visible']
            if item.checkState(1):
                item.properties['Visible'] = True
            else:
                item.properties['Visible'] = False

            changed = []
            def set_children_visible(item):
                for i in range(item.childCount()):
                    child = item.child(i)
                    child.properties['Visible'] = item.properties['Visible']
                    changed.append(child)
                    set_children_visible(child)

            # set all children to the same state
            set_children_visible(item)
            # for child in changed:
            #     child.propertiesChanged(child.properties,[[child.properties['Visible']]])