import sys , os, json, uuid
import pandas as pd
import re
sys.path.insert(0, os.path.join( os.path.dirname(__file__), "..", ".." ))
sys.path.insert(0, os.path.join( os.path.dirname(__file__), "..", "..", ".." ))
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import QMdiArea, QWidget, QDockWidget, QAction, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt, QSignalMapper
from PyQt5.QtWidgets import QApplication

from nodeeditor.utils import loadStylesheets
from nodeeditor.node_editor_window import NodeEditorWindow
from examples.example_calculator.calc_sub_window import CalculatorSubWindow
from examples.example_calculator.calc_drag_listbox import QDMDragListbox
from nodeeditor.utils import dumpException, pp
from examples.example_calculator.calc_conf import CALC_NODES

from PyQt5.QtSql import QSqlTableModel, QSqlDatabase, QSqlQuery, QSqlQueryModel
from PyQt5.QtWidgets import QMenuBar, QMenu, QAction, QToolBar, QTextEdit 
from PyQt5.QtWidgets import QSplitter, QTabWidget, QTreeView, QShortcut
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow , QToolTip
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt5.QtWidgets import QTableView, QWidget, QMessageBox, QHBoxLayout, QHeaderView
from PyQt5.QtCore import Qt, QTimer, QModelIndex, QSettings
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QKeySequence
from PyQt5.QtGui import QBrush, QColor

from excel_parser import Parser
# Enabling edge validators
from nodeeditor.node_edge import Edge
from nodeeditor.node_edge_validators import (
    edge_validator_debug,
    edge_cannot_connect_two_outputs_or_two_inputs,
    edge_cannot_connect_input_and_output_of_same_node
)
Edge.registerEdgeValidator(edge_validator_debug)
Edge.registerEdgeValidator(edge_cannot_connect_two_outputs_or_two_inputs)
Edge.registerEdgeValidator(edge_cannot_connect_input_and_output_of_same_node)


# images for the dark skin
import examples.example_calculator.qss.nodeeditor_dark_resources


DEBUG = False


class CalculatorWindow(NodeEditorWindow):

    def initUI(self):
        #node editor
        self.settings = QSettings('inho', 'node editor')  # 설정을 저장할 곳 정의

        self.name_company = 'Blenderfreak'
        self.name_product = 'Calculator NodeEditor'
        self.stylesheet_filename = os.path.join(os.path.dirname(__file__), "qss/nodeeditor.qss")
        loadStylesheets(
            os.path.join(os.path.dirname(__file__), "qss/nodeeditor-dark.qss"),
            self.stylesheet_filename
        )

        self.empty_icon = QIcon(".")

        if DEBUG:
            print("Registered nodes:")
            pp(CALC_NODES)

        self.mdiArea = QMdiArea()
        self.mdiArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdiArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdiArea.setViewMode(QMdiArea.TabbedView)
        self.mdiArea.setDocumentMode(True)
        self.mdiArea.setTabsClosable(True)
        self.mdiArea.setTabsMovable(True)

        # 분할기 생성
        splitter = QSplitter(Qt.Horizontal, self)
        # 트리뷰 생성 및 분할기에 추가
        self.tree_view = QTreeView()
        splitter.addWidget(self.tree_view)
        # 오른쪽 위젯 (탭 위젯) 생성 및 설정
        self.right_widget = QTabWidget()
        # 노드 에디터를 탭 위젯에 추가
        self.right_widget.addTab(self.mdiArea, "Node Editor")
        # 탭 위젯을 분할기에 추가
        splitter.addWidget(self.right_widget)
        # 창 크기에 따라 분할기 크기 설정
        window_width = self.size().width()
        left_width = window_width // 2
        right_width = window_width - 100
        splitter.setSizes([100, right_width])
        # 분할기를 중앙 위젯으로 설정
        self.setCentralWidget(splitter)
        self.mdiArea.subWindowActivated.connect(self.updateMenus)
        self.windowMapper = QSignalMapper(self)
        self.windowMapper.mapped[QWidget].connect(self.setActiveSubWindow)
        self.createNodesDock()
        self.createActions()
        self.createMenus()
        self.createToolBars()
        self.initDatabase()
        self.initTreeView()
        self.createStatusBar()
        self.updateMenus()
        self.readSettings()
        self.setWindowTitle("Project : 기세 Block-1")
        self.node_name = []
        self.node_data = {}  # 각 노드의 정보를 저장하는 딕셔너리를 초기화합니다.
        self.tree_view_node_level_data = {}
        self.node_edit_dialogs = {}  # UUID를 키로 하여 대화 상자 인스턴스를 저장할 딕셔너리
        


    def clearDatabase(self):
        # 데이터베이스 파일의 경로
        db_file_path = 'treeview.db'
        
        # 데이터베이스 연결 종료
        self.db.close()
        
        # 데이터베이스 파일 삭제
        if os.path.exists(db_file_path):
            os.remove(db_file_path)
            print("데이터베이스 파일 삭제됨: " + db_file_path)

    def close(self):
        # 데이터베이스 연결 종료
        self.conn.close()

    def closeEvent(self, event):
        self.mdiArea.closeAllSubWindows()
        if self.mdiArea.currentSubWindow():
            event.ignore()            
        else:
            self.writeSettings()
            self.clearDatabase()
            event.accept()
            # hacky fix for PyQt 5.14.x
            import sys
            sys.exit(0)

    def createActions(self):
        super().createActions()

        self.actClose = QAction("Cl&ose", self, statusTip="Close the active window", triggered=self.mdiArea.closeActiveSubWindow)
        self.actCloseAll = QAction("Close &All", self, statusTip="Close all the windows", triggered=self.mdiArea.closeAllSubWindows)
        self.actTile = QAction("&Tile", self, statusTip="Tile the windows", triggered=self.mdiArea.tileSubWindows)
        self.actCascade = QAction("&Cascade", self, statusTip="Cascade the windows", triggered=self.mdiArea.cascadeSubWindows)
        self.actNext = QAction("Ne&xt", self, shortcut=QKeySequence.NextChild, statusTip="Move the focus to the next window", triggered=self.mdiArea.activateNextSubWindow)
        self.actPrevious = QAction("Pre&vious", self, shortcut=QKeySequence.PreviousChild, statusTip="Move the focus to the previous window", triggered=self.mdiArea.activatePreviousSubWindow)

        self.actSeparator = QAction(self)
        self.actSeparator.setSeparator(True)

        self.actAbout = QAction("&About", self, statusTip="Show the application's About box", triggered=self.about)

    def getCurrentNodeEditorWidget(self):
        """ we're returning NodeEditorWidget here... """
        activeSubWindow = self.mdiArea.activeSubWindow()
        if activeSubWindow:
            return activeSubWindow.widget()
        return None

    def onFileNew(self):
        try:
            subwnd = self.createMdiChild()
            subwnd.widget().fileNew()
            subwnd.show()
        except Exception as e: dumpException(e)

    def onFileOpen(self):
        fnames, filter = QFileDialog.getOpenFileNames(self, 'Open graph from file', self.getFileDialogDirectory(), self.getFileDialogFilter())

        try:
            for fname in fnames:
                if fname:
                    existing = self.findMdiChild(fname)
                    if existing:
                        self.mdiArea.setActiveSubWindow(existing)
                    else:
                        # we need to create new subWindow and open the file
                        nodeeditor = CalculatorSubWindow()
                        if nodeeditor.fileLoad(fname):
                            self.statusBar().showMessage("File %s loaded" % fname, 5000)
                            nodeeditor.setTitle()
                            subwnd = self.createMdiChild(nodeeditor)
                            subwnd.show()
                        else:
                            nodeeditor.close()
        except Exception as e: dumpException(e)

    def about(self):
        QMessageBox.about(self, "About Calculator NodeEditor Example",
                "The <b>Calculator NodeEditor</b> example demonstrates how to write multiple "
                "document interface applications using PyQt5 and NodeEditor. For more information visit: "
                "<a href='https://www.blenderfreak.com/'>www.BlenderFreak.com</a>")

    def createMenus(self):
        super().createMenus()

        self.windowMenu = self.menuBar().addMenu("&Window")
        self.updateWindowMenu()
        self.windowMenu.aboutToShow.connect(self.updateWindowMenu)

        self.menuBar().addSeparator()

        self.helpMenu = self.menuBar().addMenu("&Help")
        self.helpMenu.addAction(self.actAbout)

        self.editMenu.aboutToShow.connect(self.updateEditMenu)

    def updateMenus(self):
        # print("update Menus")
        active = self.getCurrentNodeEditorWidget()
        hasMdiChild = (active is not None)

        self.actSave.setEnabled(hasMdiChild)
        self.actSaveAs.setEnabled(hasMdiChild)
        self.actClose.setEnabled(hasMdiChild)
        self.actCloseAll.setEnabled(hasMdiChild)
        self.actTile.setEnabled(hasMdiChild)
        self.actCascade.setEnabled(hasMdiChild)
        self.actNext.setEnabled(hasMdiChild)
        self.actPrevious.setEnabled(hasMdiChild)
        self.actSeparator.setVisible(hasMdiChild)

        self.updateEditMenu()

    def updateEditMenu(self):
        try:
            # print("update Edit Menu")
            active = self.getCurrentNodeEditorWidget()
            hasMdiChild = (active is not None)

            self.actPaste.setEnabled(hasMdiChild)

            self.actCut.setEnabled(hasMdiChild and active.hasSelectedItems())
            self.actCopy.setEnabled(hasMdiChild and active.hasSelectedItems())
            self.actDelete.setEnabled(hasMdiChild and active.hasSelectedItems())

            self.actUndo.setEnabled(hasMdiChild and active.canUndo())
            self.actRedo.setEnabled(hasMdiChild and active.canRedo())
        except Exception as e: dumpException(e)

    def updateWindowMenu(self):
        self.windowMenu.clear()

        # '표시' 서브메뉴에 PLC Node ID 표시 액션 추가
        toggle_plc_node_id_action = self.windowMenu.addAction('Tree View PLC Node ID 표시')
        toggle_plc_node_id_action.setCheckable(True)  # 체크 가능하도록 설정
        # 설정에서 상태를 불러옵니다
        plc_node_id_display = self.settings.value('plc_node_id_display', True, type=bool)
        toggle_plc_node_id_action.setChecked(plc_node_id_display)
        # 액션의 토글 상태가 변경될 때 호출될 슬롯을 연결합니다.
        toggle_plc_node_id_action.toggled.connect(self.toggle_plc_node_id_display)
        # 액션을 '표시' 서브메뉴에 추가합니다
        self.windowMenu.addAction(toggle_plc_node_id_action)
        
        # '표시' 서브메뉴에 'HAddress 표시' 액션 추가
        toggle_haddress_action = self.windowMenu.addAction('Tree View HAddress 표시')
        toggle_haddress_action.setCheckable(True)  # 체크 가능하도록 설정
        # 설정에서 상태를 불러옵니다
        haddress_display = self.settings.value('haddress_display', True, type=bool)
        toggle_haddress_action.setChecked(haddress_display)
        # 액션을 슬롯에 연결합니다
        toggle_haddress_action.toggled.connect(self.toggle_haddress_display)
        # 액션을 '표시' 서브메뉴에 추가합니다
        self.windowMenu.addAction(toggle_haddress_action)

        self.windowMenu.addSeparator()

        toolbar_nodes = self.windowMenu.addAction("Nodes Toolbar")
        toolbar_nodes.setCheckable(True)
        toolbar_nodes.triggered.connect(self.onWindowNodesToolbar)
        toolbar_nodes.setChecked(self.nodesDock.isVisible())

        self.windowMenu.addSeparator()

        self.windowMenu.addAction(self.actClose)
        self.windowMenu.addAction(self.actCloseAll)
        self.windowMenu.addSeparator()
        self.windowMenu.addAction(self.actTile)
        self.windowMenu.addAction(self.actCascade)
        self.windowMenu.addSeparator()
        self.windowMenu.addAction(self.actNext)
        self.windowMenu.addAction(self.actPrevious)
        self.windowMenu.addAction(self.actSeparator)

        windows = self.mdiArea.subWindowList()
        self.actSeparator.setVisible(len(windows) != 0)

        for i, window in enumerate(windows):
            child = window.widget()

            text = "%d %s" % (i + 1, child.getUserFriendlyFilename())
            if i < 9:
                text = '&' + text

            action = self.windowMenu.addAction(text)
            action.setCheckable(True)
            action.setChecked(child is self.getCurrentNodeEditorWidget())
            action.triggered.connect(self.windowMapper.map)
            self.windowMapper.setMapping(action, window)

    def onWindowNodesToolbar(self):
        if self.nodesDock.isVisible():
            self.nodesDock.hide()
        else:
            self.nodesDock.show()

    def createToolBars(self):
        toolbar = QToolBar(self)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        def add_toolbar_button(name):
            action = QAction(name, self)
            toolbar.addAction(action)
            return action
        
        new_action = add_toolbar_button('New')
        open_action = add_toolbar_button('Open')
        save_action = add_toolbar_button('Save')
        view_action = add_toolbar_button('View')

        # View_action 객체에 triggered 시그널을 연결하고, 해당 시그널이 발생했을 때 실행될 함수를 정의합니다.
        view_action.triggered.connect(self.onViewActionClicked)
        self.addToolBar(toolbar)  # 툴바 설정

    def createNodesDock(self):
        self.nodesListWidget = QDMDragListbox()

        self.nodesDock = QDockWidget("Nodes")
        self.nodesDock.setWidget(self.nodesListWidget)
        self.nodesDock.setFloating(False)

        self.addDockWidget(Qt.RightDockWidgetArea, self.nodesDock)

    def createStatusBar(self):
        self.statusBar().showMessage("Ready")

    def createMdiChild(self, child_widget=None):
        nodeeditor = child_widget if child_widget is not None else CalculatorSubWindow()
        subwnd = self.mdiArea.addSubWindow(nodeeditor)
        subwnd.setWindowIcon(self.empty_icon)
        # nodeeditor.scene.addItemSelectedListener(self.updateEditMenu)
        # nodeeditor.scene.addItemsDeselectedListener(self.updateEditMenu)
        nodeeditor.scene.history.addHistoryModifiedListener(self.updateEditMenu)
        nodeeditor.addCloseEventListener(self.onSubWndClose)
        return subwnd

    def onSubWndClose(self, widget, event):
        existing = self.findMdiChild(widget.filename)
        self.mdiArea.setActiveSubWindow(existing)

        if self.maybeSave():
            event.accept()
        else:
            event.ignore()

    def findMdiChild(self, filename):
        for window in self.mdiArea.subWindowList():
            if window.widget().filename == filename:
                return window
        return None

    def setActiveSubWindow(self, window):
        if window:
            self.mdiArea.setActiveSubWindow(window)

    def toggle_plc_node_id_display(self, checked):
        # 변경된 설정을 QSettings에 저장
        self.settings.setValue('plc_node_id_display', checked)
        # 모든 노드에 대해 텍스트 업데이트
        self.updateAllNodesName()

    def updateAllNodesName(self):
        model = self.tree_view.model()
        root_item = model.invisibleRootItem()
        
        # 재귀적으로 모든 노드의 이름을 업데이트하는 함수
        def update_name_recursive(item):
            for row in range(item.rowCount()):
                child_item = item.child(row)
                node_data = child_item.data(self.HardsConfig)
                if node_data and 'uu_id' in node_data:
                    uu_id = node_data['uu_id']

                    # 노드의 유형을 가져옵니다.
                    node_type = self.getNodeTypeByUuid(uu_id)
                    node_name = self.getNameByUuid(uu_id)
                    plc_node_id = self.getPlcNodeIdByUuid(uu_id)
                    node_id = self.getIdByUuid(uu_id)
                    haddress = self.getHaddressByUuid(uu_id)
                    catcode = self.getCatcodeByUuid(uu_id)
                    comment = self.getCommentByUuid(uu_id)

                    # 노드 유형에 따라 새로운 텍스트 형식을 설정합니다.
                    self.updateNodeText(child_item, node_type, node_name, plc_node_id, haddress, catcode, comment, "{:02d}".format(node_id))
                update_name_recursive(child_item)
        
        update_name_recursive(root_item)

    def toggle_haddress_display(self, checked):
        # 변경된 설정을 QSettings에 저장
        self.settings.setValue('haddress_display', checked)
        # 모든 노드에 대해 텍스트 업데이트
        self.updateAllNodesName()

    def onViewActionClicked(self):
        
        query = QSqlQuery()
        query.exec('SELECT * FROM nodes')

        # 데이터 보기 창이 이미 존재하고 표시되는지 확인.
        if hasattr(self, 'data_view_window') and self.data_view_window.isVisible():
            # 기존 창의 데이터를 업데이트합니다.
            self.data_view_window.updateData(query)
        else:
            # 새 데이터 보기 창을 만들고 표시합니다.
            self.data_view_window = DataViewWindow(query, self)
            self.data_view_window.show()

    def initTreeView(self):
        self.checkPoint_Bool = True
        ##########
        #self.tree_view.setStyleSheet("background-color: #333333; color: black;")  # 배경색을 어두운 회색으로 설정, 여기서 color는 글자색입니다.
        # QStandardItemModel 객체를 생성합니다.
        model = QStandardItemModel()
        self.tree_view.setModel(model)
        
        #노드 정보 변수 선언.
        self.HardsConfig = Qt.UserRole + 1
        
        # # 노드들을 추가합니다. 
        project_item = self.newNode(node_type = 'RootProject', node_name = 'New Project')
        libraries_folder = self.newNode(node_type= 'Folder', node_name = 'Libraries',parent= project_item)
        Networks_folder = self.newNode(node_type= 'Folder',node_name = 'Networks',parent= project_item)
        tcnet_item = self.newNode(node_type = 'TC-Net',node_name = 'TC-Net',parent= Networks_folder)
        station_folder = self.newNode(node_type= "Station", node_name = 'Station (Other station in hiding)', haddress= "Root Haddress", parent= project_item)

        # 더블 클릭은 해당 노드를 메인 에디터 창에 활성화 하기 위한 기능임.
        self.tree_view.setExpandsOnDoubleClick(False)
        # # 마우스 오른쪽 버튼 클릭 이벤트를 처리합니다.
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.showContextMenu)
        # 트리뷰에 더블 클릭 이벤트를 처리하는 부분을 추가합니다.
        self.tree_view.doubleClicked.connect(self.onTreeViewDoubleClicked)
        self.tree_view.setHeaderHidden(True)  # 트리뷰의 헤더를 숨깁니다.
        # 데이터가 변경되면 onDataChanged 메서드가 호출되도록 시그널을 연결합니다.
        self.tree_view.model().dataChanged.connect(self.onDataChanged)  
        # 모든 노드를 펼칩니다.
        self.tree_view.expandAll()
        
        # Setting the shortcuts
        # QShortcut(QKeySequence("Ctrl+Shift+A"), self.tree_view, self.addNodeWithShortcut)
        # QShortcut(QKeySequence("Ctrl+Shift+R"), self.tree_view, self.renameNodeWithShortcut)
        # QShortcut(QKeySequence("Ctrl+Shift+D"), self.tree_view, self.deletNodeWithShortcut)
        # QShortcut(QKeySequence("Ctrl+Shift+I"), self.tree_view, self.displayNodeDataWithShortcut)
        # QShortcut(QKeySequence("Ctrl+Shift+X"), self.tree_view, self.expendNodeWithShortcut)
        # QShortcut(QKeySequence("Ctrl+Shift+C"), self.tree_view, self.collapseNodeWithShortcut)
        
        return self.tree_view

    def deleteSelectedNode(self, selected_node):
        # 노드와 그 자식 노드들의 UUID를 저장할 리스트를 생성합니다.
        nodes_to_delete_uuids = []

        def collect_nodes_to_delete(node):
            # 선택된 노드의 UUID를 리스트에 추가합니다.
            node_data = node.data(self.HardsConfig)
            if node_data and 'uu_id' in node_data:
                nodes_to_delete_uuids.append(node_data['uu_id'])
            
            # 모든 자식 노드에 대해서도 동일한 작업을 재귀적으로 수행합니다.
            for row in range(node.rowCount()):
                child_node = node.child(row)
                collect_nodes_to_delete(child_node)

        # 선택된 노드와 자식 노드들의 UUID를 수집합니다.
        collect_nodes_to_delete(selected_node)

        # 수집된 UUID를 사용하여 데이터베이스에서 노드를 삭제합니다.
        query = QSqlQuery()
        for node_uuid in nodes_to_delete_uuids:
            query.prepare('DELETE FROM nodes WHERE uu_id = ?')
            query.addBindValue(node_uuid)
            query.exec_()

        # 최상위 노드인 경우와 그렇지 않은 경우를 분리하여 처리합니다.
        if selected_node.parent():
            # 최상위 노드가 아닌 경우
            parent_index = selected_node.parent().index()
            # 모델에서 선택된 노드를 삭제합니다.
            self.tree_view.model().removeRow(selected_node.row(), parent_index)
        else:
            # 최상위 노드인 경우
            self.tree_view.model().removeRow(selected_node.row(), QModelIndex())
        
        # 여기에 필요한 경우 추가적인 정리 작업을 수행합니다.
        # 예: 부모 노드의 자식 개수 업데이트, 뷰 갱신 등

    def printAllNodes(self):
            # 데이터베이스에서 모든 노드 정보를 검색
            query = QSqlQuery()
            query.exec('SELECT * FROM nodes')

            # 컬럼 이름 가져오기
            record = query.record()
            columns = [record.fieldName(i) for i in range(record.count())]

            # 검색된 노드 정보를 리스트로 변환
            all_nodes = []
            while query.next():
                row = [query.value(i) for i in range(record.count())]
                all_nodes.append(row)

            # 리스트를 판다스 DataFrame으로 변환
            df = pd.DataFrame(all_nodes, columns=columns)

            # DataFrame 출력
            print(df)

    def showContextMenu(self, position):
        # 현재 선택된 항목을 가져옵니다.
        selected_indexes = self.tree_view.selectedIndexes()
        
        # 메뉴를 초기화합니다.
        menu = QMenu()

        if not selected_indexes:

            # 새 노드 생성 액션을 추가합니다. TEST용  사용 안됨. 수정해야함.
            new_node_action = QAction("NewRootProject", self)
            new_node_action.triggered.connect(lambda: self.NewRootProject(node_type="Station"))
            menu.addAction(new_node_action)

            # 메뉴를 보입니다.
            menu.exec_(self.tree_view.viewport().mapToGlobal(position))
            return
        
        selected_index = selected_indexes[0]
        item = self.tree_view.model().itemFromIndex(selected_index)
        node_data = item.data(self.HardsConfig)
        
        if not node_data:
            return

        # 선택된 노드의 UUID를 검색
        node_uuid = self.getUuidFromSelectedNode()
        # 선택된 노드의 UUID로 plc_node_id를 검색
        plc_node_id = self.getPlcNodeIdByUuid(node_uuid)
        #선택된 노드의 타입 정보를 데이터 베이스에서 가지고옴.
        node_type = self.getNodeTypeByUuid(node_uuid)
        #선택된 노드의 네임 정보를 데이터 베이스에서 가지고옴.
        node_name = self.getNameByUuid(node_uuid)
        
        # "Project" 노드를 선택한 경우
        if node_type == "RootProject":
            printAllNodesAction = QAction("Print All Nodes", self)
            printAllNodesAction.triggered.connect(self.printAllNodes)
            printAllNodesAction.triggered.connect(self.onViewActionClicked)
            menu.addAction(printAllNodesAction)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            
            menu.addAction(delete_action)

        # "Station" 노드를 선택한 경우
        elif node_type == "Station":
            add_plc_action = QAction("Add PLC Project", self)
            add_plc_action.triggered.connect(lambda: self.addNewPLCProjectNode(selected_node=item))
            menu.addAction(add_plc_action)
            
            # # 동작 안됨. 확인 해야함.
            # display_data_action = QAction("Display Node Data", self)
            # display_data_action.triggered.connect(lambda: displayNodeData(self.tree_view, self.right_widget, self.HardsConfig))
            # menu.addAction(display_data_action)
        
        # "PLC_Project" 노드를 선택한 경우
        elif node_type == "PLC_Project": 
            import_action = QAction('Import PLC Project')
            import_action.triggered.connect(lambda: self.importPLC(selected_node=item))
            menu.addAction(import_action)

            # action_edit = QAction('Configure Node', self)
            # action_edit.triggered.connect(self.edit_node)
            # menu.addAction(action_edit)

        #     rename_action = QAction("Rename", self)
        #     rename_action.triggered.connect(self.renameNode)
        #     menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)

        # "PLC" 노드를 선택한 경우
        elif node_type == "PLC":
            # rename_action = QAction("Rename", self)
            # rename_action.triggered.connect(self.renameNode)
            # menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)
        
        elif node_type == "Folder":
        # """
        # 참고용 데이터 
        # | Level | Tree Directory     | Tree Type          | Tree Folder Name                                         |
        # |-------|--------------------|--------------------|----------------------------------------------------------|
        # | 0     | '00-000-00-00'     | IO                 | ['dummy']                                                |
        # | 1     | '00-000-00-**'     | IO Slot            | ['Modules']                                              |
        # | 2     | '00-000-**-**'     | Remote Slot        | ['Units']                                                |
        # | 3     | '00-***-**-**'     | CARD               | ['I/O Node', 'Controller memories', 'Tasks']             |
        # | 4     | '**-***-**-**'     | PLC                | ['Modules']                                              |
        # | 5     | 'None'             | STATION            | ['Units']                                                |
        # """
            # "PLC Units Folder" 노드를 선택한 경우, PLC 추가
            if re.match(r'^\d+-\d+-\d+-\d+$', plc_node_id) and node_name != "Station memories":
                add_plc_action = QAction("Add PLC Unit", self)
                add_plc_action.triggered.connect(lambda: self.addNewNode(node_type='PLC', selected_node=item))
                menu.addAction(add_plc_action)

            # "PLC Modules Folder" 노드를 선택한 경우, CPU추가
            elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id):
                add_cpu_action = QAction("Add CPU", self)
                add_cpu_action.triggered.connect(lambda: self.addNewNode(node_type='CARD',plc_catcode= 'PU866',  selected_node=item))
                menu.addAction(add_cpu_action)

                add_TG823_action = QAction("Add TG823", self)
                add_TG823_action.triggered.connect(lambda: self.addNewNode(node_type='CARD',plc_catcode= 'TG823',  selected_node=item))
                menu.addAction(add_TG823_action)

                add_EN811_action = QAction("Add EN811", self)
                add_EN811_action.triggered.connect(lambda: self.addNewNode(node_type='CARD',plc_catcode= 'EN811',  selected_node=item))
                menu.addAction(add_EN811_action)

            # "I/O Node Folder" 노드를 선택한 경우, 
            elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id) and node_name == 'I/O Node':
                add_RMTSLT_action = QAction("Add Remote Slot: SA912", self)
                add_RMTSLT_action.triggered.connect(lambda: self.addNewNode(node_type='Remote Slot',plc_catcode= 'SA912',  selected_node=item)) 
                menu.addAction(add_RMTSLT_action)

                add_RMTSLT_N_action = QAction("Add Remote Slot: SA912-N", self)
                add_RMTSLT_N_action.triggered.connect(lambda: self.addNewNode(node_type='Remote Slot',plc_catcode= 'SA912-N',  selected_node=item)) 
                menu.addAction(add_RMTSLT_N_action)
            
            # # "Unit Folder" 노드를 선택한 경우, 
            elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id) and node_name == 'Units':
                add_SIOUnit_action = QAction("Add SIOUnit", self)
                add_SIOUnit_action.triggered.connect(lambda: self.addNewNode(node_type='IO Slot',plc_catcode= 'SIOUnit',  selected_node=item)) 
                menu.addAction(add_SIOUnit_action)

            elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id) and node_name == 'Modules':
                IO_catcode_kind = ["DI936", "DO934", "AO934F", "AI938", "DI934T", "AB933J", "PI964", "AI928", "FL911", "PA912-NM"]
                for IOitem in IO_catcode_kind:
                    add_IO_action = QAction(f"Add IO {IOitem}", self)
                    add_IO_action.triggered.connect(lambda _=False, IOitem=IOitem: self.addNewNode(node_type='IO',plc_catcode= IOitem,  selected_node=item)) 
                    menu.addAction(add_IO_action)

        # "CPU" 노드를 선택한 경우
        elif node_type == "CARD":
            # rename_action = QAction("Rename", self)
            # rename_action.triggered.connect(self.renameNode)
            # menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)
        
        # "Remote Slot" 노드를 선택한 경우
        elif node_type == "Remote Slot":
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)

        # "IO Slot" 노드를 선택한 경우
        elif node_type == "IO Slot":
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)

        # "IO" 노드를 선택한 경우
        elif node_type == "IO":
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)

        # "Program" 노드를 선택한 경우
        elif node_type == "Program":
            # rename_action = QAction("Rename", self)
            # rename_action.triggered.connect(self.renameNode)
            # menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)

        # "Task" 노드를 선택한 경우
        elif node_type == "Task":
            add_program_action = QAction("Add Program", self)
            add_program_action.triggered.connect(self.addProgramdNode)
            menu.addAction(add_program_action)

        if node_type != 'Folder':
            action_edit = QAction('Configure Node', self)
            action_edit.triggered.connect(self.edit_node)
            menu.addAction(action_edit)

        # 공통 컨텍스트 메뉴
        com_expand_action = QAction("Expand", self)
        com_expand_action.triggered.connect(lambda: self.expand_all_children())
        menu.addAction(com_expand_action)

        com_collapse_action = QAction("Collapse", self)
        com_collapse_action.triggered.connect(lambda: self.collapse_all_children())
        menu.addAction(com_collapse_action)

        # 컨텍스트 메뉴를 표시합니다.
        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def onTreeViewDoubleClicked(self, index):
        node_data = index.data(self.HardsConfig)
        if not node_data:
            return
        uu_id = node_data["uu_id"]

        # UUID로 모든 관련 데이터를 조회합니다.
        node_type = self.getNodeTypeByUuid(uu_id)
        node_name = self.getNameByUuid(uu_id)
        id = self.getIdByUuid(uu_id)
        haddress = self.getHaddressByUuid(uu_id)
        plc_node_id = self.getPlcNodeIdByUuid(uu_id)
        catcode = self.getCatcodeByUuid(uu_id)
        comment = self.getCommentByUuid(uu_id)
        parent_plc_node_id = self.getParentPlcNodeIdByUuid(uu_id)
        child_count = self.count_children_of_parent(plc_node_id)

        # 이미 열려 있는 탭을 찾아 포커스를 이동하거나 탭을 새로 만듭니다.
        for i in range(self.right_widget.count()):
            if hasattr(self.right_widget.widget(i), 'uu_id') and self.right_widget.widget(i).uu_id == uu_id:
                self.right_widget.setCurrentIndex(i)
                return

    
        new_tab = QTextEdit()
        new_tab.setObjectName(f"tab_:{uu_id}")
        new_tab.uu_id = uu_id  # 탭에 node_id 속성을 추가

        # 가져온 노드 데이터를 포맷팅하여 텍스트 에디터에 설정합니다.
        node_info_text = f"Node Type: {node_type}\n" \
                        f"Node Name: {node_name}\n" \
                        f"Category Code: {catcode}\n" \
                        f"PLC Node ID: {plc_node_id}\n" \
                        f"ID: {id}\n" \
                        f"Haddress: {haddress}\n" \
                        f"Comment: {comment}\n" \
                        f"Parent PLC Node ID: {parent_plc_node_id}\n" \
                        f"Child Count: {child_count}"
        new_tab.setText(node_info_text)

        tab_label = f"{node_name}:{haddress}"
        self.right_widget.addTab(new_tab, tab_label)
        self.right_widget.setCurrentWidget(new_tab)


    def newNode(self, plc_node_id=None, node_type=None, node_name=None, haddress=None, catcode=None, comment=None, parent=None , row_position=None, parent_index=None):
                
        node = QStandardItem("") #노드 생성.
        uu_id = str(uuid.uuid4())  # 고유한 node_id를 생성합니다.
        node.setData({'uu_id': uu_id}, self.HardsConfig) # 노드의 커스텀 데이터에 UUID를 저장합니다.
        parent_plc_node_id = None
        parent_haddress = None
        node_id = None
        node_id_int = None
        parts = None
        if parent:  # 부모 노드가 있다면,
            parent_data = parent.data(self.HardsConfig)
            
            # UUID로 부모의 plc_node_id를 검색
            if parent_data and 'uu_id' in parent_data:
                parent_uuid = parent_data['uu_id']
                parent_plc_node_id = self.getPlcNodeIdByUuid(parent_uuid)  # 데이터베이스에서 부모의 plc_node_id 검색 메서드

            # 부모 노드의 plc_node_id를 parent_plc_node_id로 가지고 있는 노드(자식이란 뜻)를 검색
            if parent_plc_node_id:
                child_count = self.get_next_child_number(parent_plc_node_id)  # 데이터베이스에서 해당 plc node id를 부모로 가지는 노드 중 가장 큰 수를 찾음.
                node_id_int = child_count
                plc_node_id = parent_plc_node_id + '-' +str(child_count)
                
                #현재 생성되는 노드가 폴더라면, 부모의 id를 가져옴
                if node_type == 'Folder':
                    node_id = self.getIdByUuid(parent_uuid)     
                    haddress = self.getHaddressByUuid(parent_uuid)

                #새로 만든 노드라면 해당 haddress와 catcode를 생성.
                elif not haddress:
                    
                    # 상위 노드의 haddress 가져오기
                    parent_haddress = self.getHaddressByUuid(parent_uuid) if parent_uuid else None
                    
                    if parent_haddress:
                        #haddress가 유효하다면 분리
                        parts = parent_haddress.split('-')
                    # BU866 노드 생성이라면,
                    if re.match(r'^\d+-\d+-\d+-\d+-\d+$', plc_node_id):
                        catcode = "BU866"
                        node_id = "{:02d}".format(child_count)
                        haddress = "**-***-**-**" 
                    elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id):
                        catcode = catcode
                        node_id = "{:02d}".format(child_count)
                        haddress = f"{node_id}-***-**-**"
                        if catcode == 'PU866':
                            comment = 'New CPU'
                    elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id):
                        catcode = catcode
                        node_id = "{:03d}".format(child_count)
                        haddress = f"{parts[0]}-{node_id}-**-**"
                    elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id):
                        catcode = catcode
                        node_id = "{:02d}".format(child_count)
                        haddress = f"{parts[0]}-{parts[1]}-{node_id}-**"
                    elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id):
                        catcode = catcode
                        node_id = "{:02d}".format(child_count)
                        haddress = f"{parts[0]}-{parts[1]}-{parts[2]}-{node_id}"

                #기존 노드 정보를 import한다면
                else:
                    parts = haddress.split('-')
                    # BU866 노드 생성이라면,
                    if re.match(r'^\*{2}-\*{3}-\*{2}-\*{2}$', haddress):  #PLC RACK
                        node_id = "{:02d}".format(0)
                        node_id_int = 0
                    elif re.match(r'^\d{2}-\*{3}-\*{2}-\*{2}$', haddress): #CPU(CARD)
                        node_id = parts[0]
                        node_id_int = int(parts[0])
                    elif re.match(r'^\d{2}-\d{3}-\*{2}-\*{2}$', haddress): #Remote Slot
                        node_id = parts[1]
                        node_id_int = int(parts[1])
                    elif re.match(r'^\d{2}-\d{3}-\d{2}-\*{2}$', haddress): #IO Slot
                        node_id = parts[2]
                        node_id_int = int(parts[2])
                    elif re.match(r'^\d{2}-\d{3}-\d{2}-\d{2}$', haddress): #IO
                        node_id = parts[3]
                        node_id_int = int(parts[3])
                    
            else:
                plc_node_id = 0
                node_id_int = 0
                node_id = "00"
           
            # 부모 노드의 자식으로 현재 노드 추가
            if parent_index is not None and row_position is not None:  # 부모 인덱스가 제공된 경우
                self.tree_view.model().itemFromIndex(parent_index).insertRow(row_position, node)
            else:  # 부모 노드의 자식으로 현재 노드 추가
                parent.appendRow(node)
 
        else:
            # 부모 노드가 없다면, 트리의 최상위 레벨에 노드 추가
            self.tree_view.model().appendRow(node)
            node_id = "00"
            node_id_int = 0
            plc_node_id = 0

        # 데이터베이스에 노드 정보를 저장합니다.
        query = QSqlQuery()
        query.prepare('''
        INSERT INTO nodes (plc_node_id, type, id, name, uu_id, haddress, catcode, comment, parent_plc_node_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''')
        query.addBindValue(plc_node_id)
        query.addBindValue(node_type)
        query.addBindValue(node_id_int)
        query.addBindValue(node_name)
        query.addBindValue(uu_id)
        query.addBindValue(haddress)
        query.addBindValue(catcode)
        query.addBindValue(comment)
        query.addBindValue(parent_plc_node_id)
        query.exec()

        # 노드 유형에 따라 새로운 텍스트 형식을 설정합니다.
        self.updateNodeText(node, node_type, node_name, plc_node_id, haddress, catcode, comment, node_id)
        
        # 색상 설정 부분 추가
        color_mapping = {
            "RootProject": "SkyBlue",
            "root" : "Lime",
            "TC-Net": "red",
            "PLC Project": "Lime",
            'PLC Rack' : 'Lime',
            "CARD": "Lime",
            'Remote Slot' : "Lime",
            'IO Slot' : "Lime",
            "IO": "Yellow",
            "Global_Variable": "Violet",
            "Task": "orange",            
            "Folder" : "Yellow"
        }
        color = color_mapping.get(node_type, "Lime")
        node.setForeground(QBrush(QColor(color)))

        # 툴팁 설정
        node.setToolTip(f"hadd:{haddress} type:{node_type}")
        # 이름 변경 기능을 비활성화합니다.
        node.setFlags(node.flags() & ~Qt.ItemIsEditable)

        return node
    
    def addNewPLCProjectNode(self, result = None, plc_name=None, plc_catcode=None, selected_node=None):
        print('Command : addNewPLCProjectNode' )
        # 변수들의 초기값 설정
        parent = None
        makePLC_Project = False

        if not plc_name:
            plc_name = "New_PLC_Project"

        #매개변수가 주어진 경우
        if selected_node:
            parent = selected_node

        # 매개변수 노드가 주어지지 않았을 때 파일에서 정보를 가져옴()
        if makePLC_Project:
            
            # 1. 현재 스크립트의 위치를 얻습니다.
            current_script_path = os.path.dirname(os.path.abspath(__file__))
            # 2. 기본 구성 노드 파일
            file_path = os.path.join(current_script_path, 'new_plc_project_format_sample_empty.xlsx')
            result = Parser.parse_tree(self, None, file_path)
            node_names, node_data = result
            # 현재 노드의 커스텀 데이터 가져오기
            #@Stn
            plc_name = pd.DataFrame(node_data[node_names[0]]).iloc[0,0]
            plc_catcode = pd.DataFrame(node_data[node_names[0]]).iloc[0,1]
            #@HardsConfig
            HAddress = pd.DataFrame(node_data[node_names[1]]).iloc[0, 0]
            Catcodes = pd.DataFrame(node_data[node_names[1]]).iloc[0, 1]
            Comment = pd.DataFrame(node_data[node_names[1]]).iloc[0, 2]


        # dummy PLC 노드를 추가합니다.
        plc_project = self.newNode(node_type = 'PLC_Project', node_name = plc_name, haddress= None,  catcode= 'nv station', comment= None, parent= parent)
        # 최상위 "Unit" 폴더 노드 생성
        Unit_folder = self.newNode(node_type = 'Folder', node_name = 'Units', haddress= None,  catcode= None, comment= None, parent= plc_project)
        # 최상위 "Statin memories" 폴더 노드 생성
        Statin_memories_folder = self.newNode(node_type = 'Folder', node_name = 'Station memories', haddress= None,  catcode= None, comment= None, parent= plc_project)

        #self.expand_all_children()

        return Unit_folder
    
    def addNewNode(self, result = None, node_type = None, plc_name=None, HAddress = None, plc_catcode=None, Comment = None, selected_node=None , row_position=None, parent_index=None):
        # 변수들의 초기값 설정
        parent = None
        makePLC_Project = False
        
        if not plc_name:
            plc_name = node_type

        #매개변수가 주어진 경우
        if selected_node:
            parent = selected_node      
        
        if node_type == 'PLC_Project':  #nv STATION
            # dummy PLC 노드를 추가합니다.
            plc_project = self.newNode(node_type = node_type, node_name = plc_name, haddress= HAddress,  catcode= 'nv station', comment= None, parent= parent , row_position=row_position, parent_index=parent_index)  
            # 최상위 "Unit" 폴더 노드 생성
            Unit_folder = self.newNode(node_type = 'Folder', node_name = 'Units', haddress= None,  catcode= None, comment= None, parent= plc_project)
            # 최상위 "Statin memories" 폴더 노드 생성
            Statin_memories_folder = self.newNode(node_type = 'Folder', node_name = 'Station memories', haddress= None,  catcode= None, comment= None, parent= plc_project)
            
            return Unit_folder, Statin_memories_folder

        elif node_type == 'PLC':        #PLC RACK          
            # dummy PLC 노드를 추가합니다.
            plc_item = self.newNode(node_type = node_type, node_name = plc_name, haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = parent , row_position=row_position, parent_index=parent_index)        
            # 하위 모듈 폴더를 추가.
            plc_module_folder = self.newNode(node_type = 'Folder', node_name = 'Modules', haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = plc_item)
            return plc_module_folder

        elif node_type == 'CARD':

            # dummy CPU 노드를 추가합니다.
            card_item = self.newNode(node_type = node_type, node_name = 'CARD',  haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = parent , row_position=row_position, parent_index=parent_index)       
            # 하위 모듈 폴더를 추가.
            if plc_catcode == 'PU866':
                io_node_forlder = self.newNode(node_type = 'Folder', node_name = 'I/O Node', haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = card_item)
                controller_folder = self.newNode(node_type = 'Folder', node_name = 'Controller', haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = card_item)
                tasks = self.newNode(node_type = 'Folder', node_name = 'Tasks', haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = card_item)

                return io_node_forlder, controller_folder, tasks
            else:
                return None, None, None

        elif node_type == 'Remote Slot':   
            # dummy sioUnit 노드를 추가합니다.
            remotSlot = self.newNode(node_type = node_type, node_name = 'IO Node',  haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = parent, row_position=row_position, parent_index=parent_index)       
            # 하위 모듈 폴더를 추가.
            units_folder = self.newNode(node_type = 'Folder', node_name = 'Units', haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = remotSlot)
            return units_folder

        elif node_type == 'IO Slot':  
            # dummy IO Slot 노드를 추가합니다.
            sioUnit = self.newNode(node_type = node_type, node_name = 'IO Slot',  haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = parent , row_position=row_position, parent_index=parent_index)    
            # 하위 모듈 폴더를 추가.
            modules_folder = self.newNode(node_type = 'Folder', node_name = 'Modules', haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = sioUnit)
            return modules_folder

        elif node_type == 'IO':  
            # dummy sioUnit 노드를 추가합니다.
            ioUnit = self.newNode(node_type = node_type, node_name = plc_catcode,  haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = parent , row_position=row_position, parent_index=parent_index)        
            # 하위 모듈 폴더를 추가.
            #modules_folder = self.newNode(node_type = 'Folder', node_name = 'Modules', haddress= HAddress,  catcode = plc_catcode, comment = Comment, parent = ioUnit)
    
    def edit_node(self):
        indexes = self.tree_view.selectedIndexes()
        if indexes:
            index = indexes[0]
            item = self.tree_view.model().itemFromIndex(index)

            # UUID를 가져옵니다.
            node_data = item.data(self.HardsConfig)
            uuid = node_data.get('uu_id')
            
            if not uuid:
                QMessageBox.warning(self, 'Error', '노드에 UUID가 없습니다.')
                return
            # 데이터베이스에서 노드의 정보를 로드하여 QDialog로 전달합니다.
            # hasattr을 사용하여 속성 존재 여부를 확인합니다.
            if hasattr(self, 'node_edit_dialog'):
                try:
                    # isVisible을 호출하기 전에 C++ 객체가 존재하는지 확인합니다.
                    isVisible = self.node_edit_dialog.isVisible()
                except RuntimeError:
                    # C++ 객체가 삭제되었다면 예외가 발생하므로 새 객체를 생성합니다.
                    isVisible = False

                if not isVisible:
                    # 객체가 없거나 보이지 않는 경우, 새 인스턴스를 생성합니다.
                    self.node_edit_dialog = NodeEditDialog(uuid, self, self)
                    self.node_edit_dialog.show()
            else:
                # node_edit_dialog 속성이 아예 없으면 새 인스턴스를 생성합니다.
                self.node_edit_dialog = NodeEditDialog(uuid, self, self)
                self.node_edit_dialog.show()

    def updateNodeNameInView(self, uu_id, node_name):
        # 뷰에서 노드를 찾아 이름을 업데이트하는 메서드
        # 이 메서드는 노드의 UUID를 사용하여 뷰에서 해당 노드를 찾고, 새로운 이름으로 업데이트합니다.
        model = self.tree_view.model()
        root_item = model.invisibleRootItem()
        # 재귀적으로 모든 항목을 검색하여 UUID가 일치하는 노드를 찾습니다.
        def search_node(item):
            if item.data(self.HardsConfig) == {'uu_id': uu_id}:
                return item
            for row in range(item.rowCount()):
                found_item = search_node(item.child(row))
                if found_item:
                    return found_item
            return None

        node = search_node(root_item)
        if node:
            # 노드의 유형을 가져옵니다.
            node_type = self.getNodeTypeByUuid(uu_id)
            plc_node_id = self.getPlcNodeIdByUuid(uu_id)
            node_id = self.getIdByUuid(uu_id)
            haddress = self.getHaddressByUuid(uu_id)
            catcode = self.getCatcodeByUuid(uu_id)
            comment = self.getCommentByUuid(uu_id)

            # 노드 유형에 따라 새로운 텍스트 형식을 설정합니다.
            self.updateNodeText(node, node_type, node_name, plc_node_id, haddress, catcode, comment, "{:02d}".format(node_id))

    def updateNodeText(self, node=None, node_type=None, node_name=None, plc_node_id=None, haddress=None, catcode=None, comment=None, node_id=None):
        
        # 설정에 따라 표시할 텍스트를 결정합니다.
        plc_node_id_display = self.settings.value('plc_node_id_display', True, type=bool)
        haddress_display = self.settings.value('haddress_display', True, type=bool)
        node_name_text = None
        # 노드 유형에 따라 새로운 텍스트 형식을 설정합니다.
        if node_type == 'RootProject':
            node_name_text = node_name
            if plc_node_id_display:
                node_name_text += ' ' + str(plc_node_id)
            if haddress_display:
                node_name_text += ' ' + str(haddress)
            node.setText(node_name_text)
            #node.setText(f"{node_name} {plc_node_id} {haddress}")
        elif node_type == 'TC-Net':
            node_name_text = node_name
            if plc_node_id_display:
                node_name_text += ' ' + str(plc_node_id)
            if haddress_display:
                node_name_text += ' ' + str(haddress)
            node.setText(node_name_text)
            #node.setText(f"{node_name} {plc_node_id} {haddress}")
        elif node_type == 'Station':
            node_name_text = node_name
            if plc_node_id_display:
                node_name_text += ' ' + str(plc_node_id)
            if haddress_display:
                node_name_text += ' ' + str(haddress)
            node.setText(node_name_text)
            #node.setText(f"{node_name} {plc_node_id} {haddress}")
        elif node_type == 'PLC_Project':
            node_name_text = node_name +' '+ catcode
            if plc_node_id_display:
                node_name_text += ' ' + str(plc_node_id)
            if haddress_display:
                node_name_text += ' ' + str(haddress)
            node.setText(node_name_text)
            #node.setText(f"{node_name} ({catcode}) {plc_node_id} {haddress}")
        elif node_type == 'PLC':
            node_name_text = f"{node_id} ({catcode})"
            if plc_node_id_display:
                node_name_text += ' ' + str(plc_node_id)
            if haddress_display:
                node_name_text += ' ' + str(haddress)
            node.setText(node_name_text)
            #node.setText(f"{node_id} ({catcode}) {plc_node_id} {haddress}")
        elif node_type == 'CARD':
            if comment:
                node_name_text = f"{node_id} ({catcode}):{comment}"
                if plc_node_id_display:
                    node_name_text += ' ' + str(plc_node_id)
                if haddress_display:
                    node_name_text += ' ' + str(haddress)
                node.setText(node_name_text)
                #node.setText(f"{node_id} ({catcode}):{comment} {plc_node_id} {haddress}")
            else:
                node_name_text = f"{node_id} ({catcode})"
                if plc_node_id_display:
                    node_name_text += ' ' + str(plc_node_id)
                if haddress_display:
                    node_name_text += ' ' + str(haddress)
                node.setText(node_name_text)
                #node.setText(f"{node_id} ({catcode}) {plc_node_id} {haddress}")
        elif node_type == 'Remote Slot':
            node_name_text = f"{node_id} ({catcode})"
            if plc_node_id_display:
                node_name_text += ' ' + str(plc_node_id)
            if haddress_display:
                node_name_text += ' ' + str(haddress)
            node.setText(node_name_text)
            #node.setText(f"{node_id} ({catcode}) {plc_node_id} {haddress}")
        elif node_type == 'IO Slot':
            node_name_text = f"{node_id} ({catcode})"
            if plc_node_id_display:
                node_name_text += ' ' + str(plc_node_id)
            if haddress_display:
                node_name_text += ' ' + str(haddress)
            node.setText(node_name_text)
            #node.setText(f"{node_id} ({catcode}) {plc_node_id} {haddress}")
        elif node_type == 'IO':
            node_name_text = f"{node_id} ({catcode})"
            if plc_node_id_display:
                node_name_text += ' ' + str(plc_node_id)
            if haddress_display:
                node_name_text += ' ' + str(haddress)
            node.setText(node_name_text)
            #node.setText(f"{node_id} ({catcode}) {plc_node_id} {haddress}")
        elif node_type == 'Folder':
            node_name_text = node_name
            if plc_node_id_display:
                node_name_text += ' ' + str(plc_node_id)
            if haddress_display:
                node_name_text += ' ' + str(haddress)
            node.setText(node_name_text)
            #node.setText(f"{node_name} {plc_node_id} {haddress}")

    def showContextMenu(self, position):
        # 현재 선택된 항목을 가져옵니다.
        selected_indexes = self.tree_view.selectedIndexes()
        
        # 메뉴를 초기화합니다.
        menu = QMenu()

        if not selected_indexes:

            # 새 노드 생성 액션을 추가합니다. TEST용  사용 안됨. 수정해야함.
            new_node_action = QAction("NewRootProject", self)
            new_node_action.triggered.connect(lambda: self.NewRootProject(node_type="Station"))
            menu.addAction(new_node_action)

            # 메뉴를 보입니다.
            menu.exec_(self.tree_view.viewport().mapToGlobal(position))
            return
        
        selected_index = selected_indexes[0]
        item = self.tree_view.model().itemFromIndex(selected_index)
        node_data = item.data(self.HardsConfig)
        
        if not node_data:
            return

        # 선택된 노드의 UUID를 검색
        node_uuid = self.getUuidFromSelectedNode()
        # 선택된 노드의 UUID로 plc_node_id를 검색
        plc_node_id = self.getPlcNodeIdByUuid(node_uuid)
        #선택된 노드의 타입 정보를 데이터 베이스에서 가지고옴.
        node_type = self.getNodeTypeByUuid(node_uuid)
        #선택된 노드의 네임 정보를 데이터 베이스에서 가지고옴.
        node_name = self.getNameByUuid(node_uuid)
        
        # "Project" 노드를 선택한 경우
        if node_type == "RootProject":
            printAllNodesAction = QAction("Print All Nodes", self)
            printAllNodesAction.triggered.connect(self.printAllNodes)
            printAllNodesAction.triggered.connect(self.onViewActionClicked)
            menu.addAction(printAllNodesAction)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            
            menu.addAction(delete_action)

        # "Station" 노드를 선택한 경우
        elif node_type == "Station":
            add_plc_action = QAction("Add PLC Project", self)
            add_plc_action.triggered.connect(lambda: self.addNewPLCProjectNode(selected_node=item))
            menu.addAction(add_plc_action)
            
            # # 동작 안됨. 확인 해야함.
            # display_data_action = QAction("Display Node Data", self)
            # display_data_action.triggered.connect(lambda: displayNodeData(self.tree_view, self.right_widget, self.HardsConfig))
            # menu.addAction(display_data_action)
        
        # "PLC_Project" 노드를 선택한 경우
        elif node_type == "PLC_Project": 
            import_action = QAction('Import PLC Project')
            import_action.triggered.connect(lambda: self.importPLC(selected_node=item))
            menu.addAction(import_action)

            # action_edit = QAction('Configure Node', self)
            # action_edit.triggered.connect(self.edit_node)
            # menu.addAction(action_edit)

        #     rename_action = QAction("Rename", self)
        #     rename_action.triggered.connect(self.renameNode)
        #     menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)

        # "PLC" 노드를 선택한 경우
        elif node_type == "PLC":
            # rename_action = QAction("Rename", self)
            # rename_action.triggered.connect(self.renameNode)
            # menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)
        
        elif node_type == "Folder":
        # """
        # 참고용 데이터 
        # | Level | Tree Directory     | Tree Type          | Tree Folder Name                                         |
        # |-------|--------------------|--------------------|----------------------------------------------------------|
        # | 0     | '00-000-00-00'     | IO                 | ['dummy']                                                |
        # | 1     | '00-000-00-**'     | IO Slot            | ['Modules']                                              |
        # | 2     | '00-000-**-**'     | Remote Slot        | ['Units']                                                |
        # | 3     | '00-***-**-**'     | CARD               | ['I/O Node', 'Controller memories', 'Tasks']             |
        # | 4     | '**-***-**-**'     | PLC                | ['Modules']                                              |
        # | 5     | 'None'             | STATION            | ['Units']                                                |
        # """
            # "PLC Units Folder" 노드를 선택한 경우, PLC 추가
            if re.match(r'^\d+-\d+-\d+-\d+$', plc_node_id) and node_name != "Station memories":
                add_plc_action = QAction("Add PLC Unit", self)
                add_plc_action.triggered.connect(lambda: self.addNewNode(node_type='PLC', selected_node=item))
                menu.addAction(add_plc_action)

            # "PLC Modules Folder" 노드를 선택한 경우, CPU추가
            elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id):
                add_cpu_action = QAction("Add CPU", self)
                add_cpu_action.triggered.connect(lambda: self.addNewNode(node_type='CARD',plc_catcode= 'PU866',  selected_node=item))
                menu.addAction(add_cpu_action)

                add_TG823_action = QAction("Add TG823", self)
                add_TG823_action.triggered.connect(lambda: self.addNewNode(node_type='CARD',plc_catcode= 'TG823',  selected_node=item))
                menu.addAction(add_TG823_action)

                add_EN811_action = QAction("Add EN811", self)
                add_EN811_action.triggered.connect(lambda: self.addNewNode(node_type='CARD',plc_catcode= 'EN811',  selected_node=item))
                menu.addAction(add_EN811_action)

            # "I/O Node Folder" 노드를 선택한 경우, 
            elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id) and node_name == 'I/O Node':
                add_RMTSLT_action = QAction("Add Remote Slot: SA912", self)
                add_RMTSLT_action.triggered.connect(lambda: self.addNewNode(node_type='Remote Slot',plc_catcode= 'SA912',  selected_node=item)) 
                menu.addAction(add_RMTSLT_action)

                add_RMTSLT_N_action = QAction("Add Remote Slot: SA912-N", self)
                add_RMTSLT_N_action.triggered.connect(lambda: self.addNewNode(node_type='Remote Slot',plc_catcode= 'SA912-N',  selected_node=item)) 
                menu.addAction(add_RMTSLT_N_action)
            
            # # "Unit Folder" 노드를 선택한 경우, 
            elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id) and node_name == 'Units':
                add_SIOUnit_action = QAction("Add SIOUnit", self)
                add_SIOUnit_action.triggered.connect(lambda: self.addNewNode(node_type='IO Slot',plc_catcode= 'SIOUnit',  selected_node=item)) 
                menu.addAction(add_SIOUnit_action)

            elif re.match(r'^\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+-\d+$', plc_node_id) and node_name == 'Modules':
                IO_catcode_kind = ["DI936", "DO934", "AO934F", "AI938", "DI934T", "AB933J", "PI964", "AI928", "FL911", "PA912-NM"]
                for IOitem in IO_catcode_kind:
                    add_IO_action = QAction(f"Add IO {IOitem}", self)
                    add_IO_action.triggered.connect(lambda _=False, IOitem=IOitem: self.addNewNode(node_type='IO',plc_catcode= IOitem,  selected_node=item)) 
                    menu.addAction(add_IO_action)

        # "CPU" 노드를 선택한 경우
        elif node_type == "CARD":
            # rename_action = QAction("Rename", self)
            # rename_action.triggered.connect(self.renameNode)
            # menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)
        
        # "Remote Slot" 노드를 선택한 경우
        elif node_type == "Remote Slot":
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)

        # "IO Slot" 노드를 선택한 경우
        elif node_type == "IO Slot":
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)

        # "IO" 노드를 선택한 경우
        elif node_type == "IO":
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)

        # "Program" 노드를 선택한 경우
        elif node_type == "Program":
            # rename_action = QAction("Rename", self)
            # rename_action.triggered.connect(self.renameNode)
            # menu.addAction(rename_action)

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteSelectedNode(selected_node=item))
            menu.addAction(delete_action)

        # "Task" 노드를 선택한 경우
        elif node_type == "Task":
            add_program_action = QAction("Add Program", self)
            add_program_action.triggered.connect(self.addProgramdNode)
            menu.addAction(add_program_action)

        if node_type != 'Folder':
            action_edit = QAction('Configure Node', self)
            action_edit.triggered.connect(self.edit_node)
            menu.addAction(action_edit)

        # 공통 컨텍스트 메뉴
        com_expand_action = QAction("Expand", self)
        com_expand_action.triggered.connect(lambda: self.expand_all_children())
        menu.addAction(com_expand_action)

        com_collapse_action = QAction("Collapse", self)
        com_collapse_action.triggered.connect(lambda: self.collapse_all_children())
        menu.addAction(com_collapse_action)

        # 컨텍스트 메뉴를 표시합니다.
        menu.exec(self.tree_view.viewport().mapToGlobal(position))

    def importPLC(self, selected_node=None):
        def importPlcFunction():
        # 엑셀 파일을 열어 대화창을 표시합니다.
            file_path, _ = QFileDialog.getOpenFileName(self, "Import PLC Function", "", "Excel Files (*.xlsx)")
            
            if file_path:
                # 파서 함수를 사용하여 엑셀 파일에서 트리 구조를 파싱합니다.
                return Parser.parse_tree(self, None, file_path)
            else:
                return None, None  # 빈 튜플 반환
        
        if not selected_node:
            return
        # 엑셀 파일을 Import 및 Parsing.
        result = importPlcFunction()
        
        #import 창을 열었다가, 파일을 추가하지 않고 창을 닫게되면, 리턴
        if result == (None, None):
            return

        #기존 노드 삭제 절차
        #1. 기존 노드 위치 정보 저장.
        parent = selected_node.parent()
        parent_index = selected_node.parent().index()  # 선택된 노드의 부모 인덱스
        row_position = selected_node.row()  # 선택된 노드의 행 위치
        #2. 기존 노드 삭제 메서드 실행.
        self.deleteSelectedNode(selected_node=selected_node)
        
        # # 1. 현재 스크립트의 위치를 얻습니다.
        # current_script_path = os.path.dirname(os.path.abspath(__file__))
        # # 2. 기본 구성 노드 파일
        # file_path = os.path.join(current_script_path, 'haddress_format_sample.xlsx')
        # result = Parser.parse_tree(self, None, file_path)
        node_names, node_data = result
        
        # 현재 노드의 커스텀 데이터 가져오기
        #@Stn
        plc_name = pd.DataFrame(node_data[node_names[0]]).iloc[0,0]
        plc_catcode = pd.DataFrame(node_data[node_names[0]]).iloc[0,1]
        
        #@HardsConfig
        HAddress = pd.DataFrame(node_data[node_names[1]]).iloc[:, 0]
        Catcodes = pd.DataFrame(node_data[node_names[1]]).iloc[:, 1]
        Comment = pd.DataFrame(node_data[node_names[1]]).iloc[:, 2]

        def custom_sort(haddress):
            return [f"{int(y):05}" if y.isdigit() else y for y in haddress.split('-')]
        
        
        df = pd.DataFrame(node_data[node_names[1]])
        df = df.iloc[df['HAddress'].apply(custom_sort).argsort()]

        #plc station 노드 생성.        
        unit_folder, Statin_memories_folder = self.addNewNode(node_type = 'PLC_Project',  #PLC Project
                                                                    plc_name = plc_name, 
                                                                    HAddress= None,  
                                                                    plc_catcode= 'nv station', 
                                                                    Comment= None, 
                                                                    selected_node=parent,
                                                                    row_position= row_position, 
                                                                    parent_index= parent_index)

        for index, row in df.iterrows():
            haddress = row['HAddress']
            catcode = row['Catcode']
            comment = row['Comment']
            
            if re.match(r'^\*{2}-\*{3}-\*{2}-\*{2}$', haddress):  #PLC RACK
                plc_module_folder = self.addNewNode(node_type = 'PLC', 
                                                    plc_name = plc_name, 
                                                    HAddress= haddress,  
                                                    plc_catcode= catcode, 
                                                    Comment= comment, 
                                                    selected_node = unit_folder
                                                    )
                
            elif re.match(r'^\d{2}-\*{3}-\*{2}-\*{2}$', haddress): #CARD
                io_node_forlder, controller_folder, tasks = self.addNewNode(node_type = 'CARD', 
                                                                            plc_name = None, 
                                                                            HAddress = haddress,  
                                                                            plc_catcode = catcode, 
                                                                            Comment = comment, 
                                                                            selected_node = plc_module_folder  
                                                                            )
            
            elif re.match(r'^\d{2}-\d{3}-\*{2}-\*{2}$', haddress): #Remote Slot
                unit_module_folder = self.addNewNode(node_type = 'Remote Slot', 
                                        plc_name = None, 
                                        HAddress= haddress,  
                                        plc_catcode= catcode, 
                                        Comment= comment, 
                                        selected_node= io_node_forlder 
                                        )

            elif re.match(r'^\d{2}-\d{3}-\d{2}-\*{2}$', haddress): #IO Slot
                sio_module_folder = self.addNewNode(node_type = 'IO Slot', 
                                        plc_name = None, 
                                        HAddress= haddress,  
                                        plc_catcode= catcode, 
                                        Comment= comment, 
                                        selected_node= unit_module_folder 
                                        )
            
            elif re.match(r'^\d{2}-\d{3}-\d{2}-\d{2}$', haddress): #IO Slot
                #sio_module_folder = self.addNewNode(node_type = 'IO', 
                self.addNewNode(node_type = 'IO', 
                                        plc_name = None, 
                                        HAddress= haddress,  
                                        plc_catcode= catcode, 
                                        Comment= comment, 
                                        selected_node= sio_module_folder 
                                        )
                
            self.expand_all_children() #모든 노드 펼침
    
    def NewRootProject(self):
        # 노드들을 추가합니다. 
        project_item = self.newNode(node_type = 'Project', node_name = 'New Project')
        libraries_folder = self.newNode(node_type= 'Folder', node_name = 'Libraries',parent= project_item)
        Networks_folder = self.newNode(node_type= 'Folder',node_name = 'Networks',parent= project_item)
        tcnet_item = self.newNode(node_type = 'TC-Net',node_name = 'TC-Net',parent= Networks_folder)
        station_folder = self.newNode(node_type= "Station", node_name = 'Station (Other station in hiding)', haddress= "Root Haddress", parent= project_item)

    def addProgramdNode(self):
        # 현재 선택된 항목을 가져옵니다.
        selected_indexes = self.tree_view.selectedIndexes()
        if not selected_indexes:
            return
        selected_index = selected_indexes[0]
        parent = self.tree_view.model().itemFromIndex(selected_index)

    def onTabCloseRequested(self, index):
        self.right_widget.removeTab(index)
    
    def initWindowClass(self, window_class):
        self.window_class = window_class
    
    def expand_all_children(self, index=None):
        if index is None:
            selected_indexes = self.tree_view.selectedIndexes()
            if not selected_indexes:
                return
            index = selected_indexes[0]

        if not index.isValid():
            return

        self.tree_view.expand(index)

        model = self.tree_view.model()
        for row in range(model.rowCount(index)):
            child_index = model.index(row, 0, index)
            self.expand_all_children(child_index)
    
    def collapse_all_children(self, index=None):
        if index is None:
            selected_indexes = self.tree_view.selectedIndexes()
            if not selected_indexes:
                return
            index = selected_indexes[0]

        if not index.isValid():
            return
        
        self.tree_view.collapse(index)
        
        model = self.tree_view.model()
        for row in range(model.rowCount(index)):
            child_index = model.index(row, 0, index)
            self.collapse_all_children(child_index)
    
    def onTreeViewDoubleClicked(self, index):
        node_data = index.data(self.HardsConfig)
        if not node_data:
            return
        uu_id = node_data["uu_id"]

        # UUID로 모든 관련 데이터를 조회합니다.
        node_type = self.getNodeTypeByUuid(uu_id)
        node_name = self.getNameByUuid(uu_id)
        id = self.getIdByUuid(uu_id)
        haddress = self.getHaddressByUuid(uu_id)
        plc_node_id = self.getPlcNodeIdByUuid(uu_id)
        catcode = self.getCatcodeByUuid(uu_id)
        comment = self.getCommentByUuid(uu_id)
        parent_plc_node_id = self.getParentPlcNodeIdByUuid(uu_id)
        child_count = self.count_children_of_parent(plc_node_id)

        # 이미 열려 있는 탭을 찾아 포커스를 이동하거나 탭을 새로 만듭니다.
        for i in range(self.right_widget.count()):
            if hasattr(self.right_widget.widget(i), 'uu_id') and self.right_widget.widget(i).uu_id == uu_id:
                self.right_widget.setCurrentIndex(i)
                return

    
        new_tab = QTextEdit()
        new_tab.setObjectName(f"tab_:{uu_id}")
        new_tab.uu_id = uu_id  # 탭에 node_id 속성을 추가

        # 가져온 노드 데이터를 포맷팅하여 텍스트 에디터에 설정합니다.
        node_info_text = f"Node Type: {node_type}\n" \
                        f"Node Name: {node_name}\n" \
                        f"Category Code: {catcode}\n" \
                        f"PLC Node ID: {plc_node_id}\n" \
                        f"ID: {id}\n" \
                        f"Haddress: {haddress}\n" \
                        f"Comment: {comment}\n" \
                        f"Parent PLC Node ID: {parent_plc_node_id}\n" \
                        f"Child Count: {child_count}"
        new_tab.setText(node_info_text)

        tab_label = f"{node_name}:{haddress}"
        self.right_widget.addTab(new_tab, tab_label)
        self.right_widget.setCurrentWidget(new_tab)

    # QStandardItemModel.dataChanged() 시그널이 발생하면 호출되는 메서드입니다.
    # 트리 수정 시, 메인 애디터 창을 검색 후, 열려 있다면 해당 창도 업데이트 함.
    def onDataChanged(self, index):
        return
        # 수정된 아이템의 인덱스와 데이터를 출력합니다.
        item = index.model().itemFromIndex(index)
        #print(f"Item {item.text()} at index {index.row()} has been modified.")
        # 노드 데이터를 업데이트합니다.
        node_data = item.data(self.HardsConfig)

        if node_data:
            node_data["name"] = item.text()
            # 업데이트된 노드가 현재 열려 있는 탭 창에 있는지 확인합니다.
            node_id = node_data["uu_id"]
            node_type = node_data["type"]
            node_name = node_data["name"]
            # 이미 열려 있는 탭을 찾습니다.
            for i in range(self.right_widget.count()):
                if hasattr(self.right_widget.widget(i), 'node_id') and self.right_widget.widget(i).node_id == node_id:
                    self.right_widget.setTabText(i, f"{node_type}:{node_name}")
                    # 탭이 이미 열려 있는 경우 이름을 변경하고 포커스만 이동합니다.
                    self.right_widget.setCurrentIndex(i)                
                    break
    
    ### 데이터베이스에서 특정 속성을 조회합니다.
    def getNodeAttributeByUuid(self, uu_id, attribute):
        """
        주어진 UUID에 해당하는 노드의 특정 속성을 조회합니다.
        """
        query = QSqlQuery()
        query.prepare(f'SELECT {attribute} FROM nodes WHERE uu_id = :uu_id')
        query.bindValue(":uu_id", uu_id)
        if query.exec():
            if query.next():
                return query.value(0)
        return None

    def getPlcNodeIdByUuid(self, uu_id):
        """
        주어진 UUID에 해당하는 노드의 PLC 노드 ID를 조회합니다.
        """
        return self.getNodeAttributeByUuid(uu_id, 'plc_node_id')

    def getNodeTypeByUuid(self, uu_id):
        """
        주어진 UUID에 해당하는 노드의 타입을 조회합니다.
        """
        return self.getNodeAttributeByUuid(uu_id, 'type')

    def getIdByUuid(self, uu_id):
        """
        주어진 UUID에 해당하는 노드의 ID를 조회합니다.
        """
        return self.getNodeAttributeByUuid(uu_id, 'id')

    def getNameByUuid(self, uu_id):
        """
        주어진 UUID에 해당하는 노드의 이름을 조회합니다.
        """
        return self.getNodeAttributeByUuid(uu_id, 'name')

    def getHaddressByUuid(self, uu_id):
        """
        주어진 UUID에 해당하는 노드의 Haddress를 조회합니다.
        """
        return self.getNodeAttributeByUuid(uu_id, 'haddress')

    def getCatcodeByUuid(self, uu_id):
        """
        주어진 UUID에 해당하는 노드의 카테고리 코드를 조회합니다.
        """
        return self.getNodeAttributeByUuid(uu_id, 'catcode')

    def getCommentByUuid(self, uu_id):
        """
        주어진 UUID에 해당하는 노드의 코멘트를 조회합니다.
        """
        return self.getNodeAttributeByUuid(uu_id, 'comment')

    def getParentPlcNodeIdByUuid(self, uu_id):
        """
        주어진 UUID에 해당하는 노드의 부모 PLC 노드 ID를 조회합니다.
        """
        return self.getNodeAttributeByUuid(uu_id, 'parent_plc_node_id')

    def count_children_of_parent(self, parent_plc_node_id):
        """
        주어진 부모 PLC 노드 ID에 대한 자식 노드의 개수를 반환합니다.
        """
        query = QSqlQuery()
        query.prepare('SELECT COUNT(*) FROM nodes WHERE parent_plc_node_id = :parent_plc_node_id')
        query.bindValue(":parent_plc_node_id", parent_plc_node_id)
        if query.exec():
            if query.next():
                return query.value(0)
        return 0

    def get_next_child_number(self, parent_plc_node_id):
        """부모 plc_node_id에 대한 자식 노드의 'id' 중 가장 큰 값을 찾아서 반환"""
        query = QSqlQuery()
        query.prepare('SELECT MAX(id) FROM nodes WHERE parent_plc_node_id = ?')
        query.addBindValue(parent_plc_node_id)
        query.exec()
        if query.next():
            max_id = query.value(0)
            if max_id is not None and max_id != "":
                return max_id + 1
            else:
                return 0  # 자식 노드가 없으면 '0'을 반환

    def getUuidFromSelectedNode(self):
        """
        트리 뷰에서 선택된 노드의 UUID를 가져옵니다.
        """
        selected_indexes = self.tree_view.selectedIndexes()
        if not selected_indexes:
            return None  # 선택된 노드가 없으면 None 반환

        selected_index = selected_indexes[0]  # 첫 번째 선택된 노드를 사용
        item = self.tree_view.model().itemFromIndex(selected_index)

        # 선택된 노드에서 UUID를 추출합니다.
        node_data = item.data(self.HardsConfig)
        if not node_data or 'uu_id' not in node_data:
            return None  # UUID가 없으면 None 반환

        return node_data['uu_id']

    def updateNodeAttributeByUuid(self, uu_id, attribute, value):
        # 데이터베이스에 안전하게 값을 업데이트하기 위해 parameterized query를 사용합니다.
        query = QSqlQuery()
        update_query = f'UPDATE nodes SET {attribute} = ? WHERE uu_id = ?'
        query.prepare(update_query)
        query.bindValue(0, value)
        query.bindValue(1, uu_id)

        if query.exec_():
            print("업데이트 성공.")
        else:
            print("업데이트 오류:", query.lastError().text())

    def initDatabase(self):
        # 데이터베이스 파일이 존재하는지 확인
        db_file_path = 'treeview.db'
        
        # 데이터베이스 파일이 이미 존재하면 삭제
        if os.path.exists(db_file_path):
            print("기존 데이터 베이스 삭제:" + db_file_path)
            os.remove(db_file_path)

        # 데이터베이스 연결
        self.db = QSqlDatabase.addDatabase('QSQLITE')
        self.db.setDatabaseName(db_file_path)

        # 데이터베이스 열기
        if not self.db.open():
            print("데이터베이스를 열 수 없습니다.")
            return

        # 쿼리 객체 생성
        query = QSqlQuery()

        # 새 테이블 생성
        query.exec('''
        CREATE TABLE IF NOT EXISTS nodes (
            plc_node_id TEXT,
            type TEXT,
            id INTEGER,
            name TEXT,
            uu_id TEXT PRIMARY KEY,
            haddress TEXT,
            catcode TEXT,
            comment TEXT,
            parent_plc_node_id TEXT
        )
        ''')
    
    def close(self):
        # 데이터베이스 연결 종료
        self.conn.close()
    
    def clearDatabase(self):
        # 데이터베이스 파일의 경로
        db_file_path = 'treeview.db'
        
        # 데이터베이스 연결 종료
        self.db.close()
        
        # 데이터베이스 파일 삭제
        if os.path.exists(db_file_path):
            os.remove(db_file_path)
            print("데이터베이스 파일 삭제됨: " + db_file_path)

# 데이터 뷰
class DataViewWindow(QMainWindow):
    def __init__(self, query, parent=None):
        super(DataViewWindow, self).__init__(parent)
        self.setWindowTitle("Node Data View")
        
        # 테이블 뷰를 설정합니다.
        self.tableView = QTableView(self)
        
        model = QSqlQueryModel()
        model.setQuery(query)
        self.tableView.setModel(model)

        # 레이아웃을 설정합니다.
        layout = QVBoxLayout()
        layout.addWidget(self.tableView)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        # 열 너비를 자동으로 조정하도록 설정합니다.
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        

    def updateData(self, new_query):
        if hasattr(self, 'model'):
            self.model.setQuery(new_query)
        else:
            self.model = QSqlQueryModel()
            self.model.setQuery(new_query)            
            self.tableView.setModel(self.model)
            

# 노드 애디터 뷰
class NodeEditDialog(QDialog):
    def __init__(self, uu_id, main_node_edit, parent=None):
        super().__init__(parent)
        self.uu_id = uu_id  # Save the uu_id as an instance variable
        self.main_node_edit = main_node_edit  # Save the reference to the main application or database helper class
        self.init_ui()

    def init_ui(self):
        # Set the window title and other properties if needed
        self.setWindowTitle('Edit Node')

        # Load data from the database
        self.load_data_from_db()

        # Layout setup
        layout = QVBoxLayout(self)

        self.childrenCountLabel = QLabel('Children Count:', self)
        self.childrenCountLabel.setText(f'Children Count: {self.children_count}')
        layout.addWidget(self.childrenCountLabel)  # Add label to layout

        # Create UI components with the loaded data
        # Node Type
        self.nodeTypeLineEdit = QLineEdit(self)
        self.nodeTypeLineEdit.setText(self.node_type)
        self.nodeTypeLineEdit.setReadOnly(True)  # 편집 불가능하도록 설정
        # 스타일 변경: 배경색을 연한 회색으로, 테두리 없음
        self.nodeTypeLineEdit.setStyleSheet("QLineEdit { background: lightgrey; border: none; }")
        layout.addWidget(QLabel('Node Type:'))
        layout.addWidget(self.nodeTypeLineEdit)

        # PLC Node ID
        self.plcNodeIdLineEdit = QLineEdit(self)
        self.plcNodeIdLineEdit.setText(self.plc_node_id)
        self.plcNodeIdLineEdit.setReadOnly(True)  # 편집 불가능하도록 설정
        # 스타일 변경: 배경색을 연한 회색으로, 테두리 없음
        self.plcNodeIdLineEdit.setStyleSheet("QLineEdit { background: lightgrey; border: none; }")
        layout.addWidget(QLabel('PLC Node ID:'))
        layout.addWidget(self.plcNodeIdLineEdit)

        # Node ID
        self.nodeIdLineEdit = QLineEdit(self)
        self.nodeIdLineEdit.setText(str(self.node_id))  # Convert to string
        self.nodeIdLineEdit.setReadOnly(True)  # 편집 불가능하도록 설정
        # 스타일 변경: 배경색을 연한 회색으로, 테두리 없음
        self.nodeIdLineEdit.setStyleSheet("QLineEdit { background: lightgrey; border: none; }")
        layout.addWidget(QLabel('Node ID:'))
        layout.addWidget(self.nodeIdLineEdit)


        # Hardware Address
        self.haddressLineEdit = QLineEdit(self)
        self.haddressLineEdit.setText(self.haddress)
        self.haddressLineEdit.setReadOnly(True)  # 편집 불가능하도록 설정
        # 스타일 변경: 배경색을 연한 회색으로, 테두리 없음
        self.haddressLineEdit.setStyleSheet("QLineEdit { background: lightgrey; border: none; }")
        layout.addWidget(QLabel('Hardware Address:'))
        layout.addWidget(self.haddressLineEdit)

        # Category Code
        self.catcodeLineEdit = QLineEdit(self)
        self.catcodeLineEdit.setText(self.catcode)
        self.catcodeLineEdit.setReadOnly(True)  # 편집 불가능하도록 설정
        # 스타일 변경: 배경색을 연한 회색으로, 테두리 없음
        self.catcodeLineEdit.setStyleSheet("QLineEdit { background: lightgrey; border: none; }")
        layout.addWidget(QLabel('Category Code:'))
        layout.addWidget(self.catcodeLineEdit)

        # Parent PLC Node ID
        self.parentPlcNodeIdLineEdit = QLineEdit(self)
        self.parentPlcNodeIdLineEdit.setText(self.parent_plc_node_id)
        self.parentPlcNodeIdLineEdit.setReadOnly(True)  # 편집 불가능하도록 설정
        # 스타일 변경: 배경색을 연한 회색으로, 테두리 없음
        self.parentPlcNodeIdLineEdit.setStyleSheet("QLineEdit { background: lightgrey; border: none; }")
        layout.addWidget(QLabel('Parent PLC Node ID:'))
        layout.addWidget(self.parentPlcNodeIdLineEdit)

        # Name
        self.nameLineEdit = QLineEdit(self)
        self.nameLineEdit.setText(self.name)
        layout.addWidget(QLabel('Name:'))
        layout.addWidget(self.nameLineEdit)

        # Comment
        self.commentTextEdit = QTextEdit(self)
        self.commentTextEdit.setText(self.comment)
        layout.addWidget(QLabel('Comment:'))
        layout.addWidget(self.commentTextEdit)

        # Confirm and Cancel buttons
        self.btn_ok = QPushButton('확인', self)
        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel = QPushButton('취소', self)
        self.btn_cancel.clicked.connect(self.reject)
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.btn_ok)
        buttons_layout.addWidget(self.btn_cancel)
        layout.addLayout(buttons_layout)

    def load_data_from_db(self):
        # 데이터베이스에서 노드의 정보를 가져와서 UI에 설정합니다.
        self.node_type = self.main_node_edit.getNodeTypeByUuid(self.uu_id)
        self.name = self.main_node_edit.getNameByUuid(self.uu_id)
        self.plc_node_id = self.main_node_edit.getPlcNodeIdByUuid(self.uu_id)
        self.node_id = self.main_node_edit.getIdByUuid(self.uu_id)
        self.haddress = self.main_node_edit.getHaddressByUuid(self.uu_id)
        self.catcode = self.main_node_edit.getCatcodeByUuid(self.uu_id)
        self.comment = self.main_node_edit.getCommentByUuid(self.uu_id)
        self.parent_plc_node_id = self.main_node_edit.getParentPlcNodeIdByUuid(self.uu_id)
        # 자식 노드의 수를 계산합니다.
        self.children_count = self.main_node_edit.count_children_of_parent(self.plc_node_id)
  
    def accept(self):
        # 변경된 데이터를 데이터베이스에 저장합니다.
        # 입력된 값을 가져옵니다.
        updated_name = self.nameLineEdit.text()
        #updated_node_type = self.nodeTypeLineEdit.text()
        #updated_plc_node_id = self.plcNodeIdLineEdit.text()
        #updated_node_id = int(self.nodeIdLineEdit.text())  # node_id가 정수라면, 저장하기 전에 형변환을 고려해야 할 수 있습니다.
        #updated_haddress = self.haddressLineEdit.text()
        #updated_catcode = self.catcodeLineEdit.text()
        updated_comment = self.commentTextEdit.toPlainText()
        #updated_parent_plc_node_id = self.parentPlcNodeIdLineEdit.text()

        # 데이터베이스를 업데이트합니다.
        self.main_node_edit.updateNodeAttributeByUuid(self.uu_id, 'name', updated_name)
        #self.main_node_edit.updateNodeAttributeByUuid(self.uu_id, 'type', updated_node_type)  # 'node_type' 대신 'type' 사용
        #self.main_node_edit.updateNodeAttributeByUuid(self.uu_id, 'plc_node_id', updated_plc_node_id)
        #self.main_node_edit.updateNodeAttributeByUuid(self.uu_id, 'id', int(updated_node_id))  # 'node_id' 대신 'id' 사용
        #self.main_node_edit.updateNodeAttributeByUuid(self.uu_id, 'haddress', updated_haddress)
        #self.main_node_edit.updateNodeAttributeByUuid(self.uu_id, 'catcode', updated_catcode)
        self.main_node_edit.updateNodeAttributeByUuid(self.uu_id, 'comment', updated_comment)
        #self.main_node_edit.updateNodeAttributeByUuid(self.uu_id, 'parent_plc_node_id', updated_parent_plc_node_id)
        
        # 메인 뷰의 노드 이름도 업데이트합니다.
        self.main_node_edit.updateNodeNameInView(self.uu_id, updated_name)
        super().accept()  # 원래 QDialog의 accept 메서드를 호출합니다.
        self.deleteLater()  # 다이얼로그 인스턴스를 예약 삭제합니다.

    def reject(self):
        super().reject()  # 원래 QDialog의 reject 메서드를 호출합니다.
        self.deleteLater()  # 다이얼로그 인스턴스를 예약 삭제합니다.


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # print(QStyleFactory.keys())
    app.setStyle('Fusion')

    wnd = CalculatorWindow()
    wnd.show()

    sys.exit(app.exec_())
