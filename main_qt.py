import sys
import os
import json
import uuid
import shutil
import zipfile
import tempfile
from datetime import datetime
import platform # Added for OS detection

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                            QPushButton, QLabel, QFileDialog, QMessageBox, QTreeWidget,
                            QTreeWidgetItem, QLineEdit, QFrame, QSplitter, QRadioButton,
                            QCheckBox, QGroupBox, QInputDialog, QStatusBar, QComboBox, QDialog,
                            QTextEdit, QStyle, QTabWidget) # Added QStyle and QTabWidget
from PyQt6.QtCore import Qt, QSize, QProcess, QUrl # Added QProcess, QUrl
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QDesktopServices, QTextCursor # 添加 QTextCursor

class PackManagerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minecraft Bedrock 服务器与存档管理器 v8.3 (PyQt6版)") # 版本更新
        self.setMinimumSize(1200, 800)

        # Data storage
        self.server_root_path = ""
        self.loaded_world_name = ""
        self.loaded_world_path = ""
        self.world_behavior_packs_data = []
        self.world_resource_packs_data = []
        self.world_behavior_json_path = ""
        self.world_resource_json_path = ""
        self.server_pack_uuid_to_manifest_details = {} # New: To map UUID to manifest name & other details

        # Server Process
        self.server_process = None
        if platform.system() == "Windows":
            self.server_executable_name = "bedrock_server.exe"
        elif platform.system() == "Linux":
            self.server_executable_name = "bedrock_server" # May need chmod +x
        else: # macOS or other
            self.server_executable_name = "bedrock_server" # Adjust as needed
            QMessageBox.information(self, "提示", f"服务器可执行文件名默认为 '{self.server_executable_name}'. 如果不同,请在代码中修改.")


        # Set styles
        self.setup_styles()

        # Create main window widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Create top control bar
        self.create_top_controls(main_layout)

        # Create main splitter window
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        # --- 修改左侧面板为 QTabWidget ---
        self.left_tab_widget = QTabWidget() # 创建 QTabWidget
        main_splitter.addWidget(self.left_tab_widget) # 将 QTabWidget 添加到分割器

        # 创建各个部分,并将它们添加为标签页
        world_management_group = self.create_world_management_section()
        self.left_tab_widget.addTab(world_management_group, "世界管理")

        server_pack_management_group = self.create_server_pack_management_section()
        self.left_tab_widget.addTab(server_pack_management_group, "服务器包管理")
        
        server_control_group = self.create_server_control_section()
        self.left_tab_widget.addTab(server_control_group, "服务器控制台")
        # --- 左侧面板修改结束 ---
        
        # 右侧面板 (保持不变)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        main_splitter.addWidget(right_panel)

        # 这些方法仍然直接添加到 right_layout
        self.create_pack_import_section(right_layout)
        self.create_world_pack_management_section(right_layout)

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status("请先加载服务器根目录")

        # Set splitter ratio
        main_splitter.setSizes([550, 650]) # 调整分割比例以适应更宽的服务器包列表

        # Initialize disable all world related controls
        self.disable_all_world_specific_controls()
        self.disable_server_specific_controls() # New: disable server controls initially

    def setup_styles(self):
        """设置应用程序样式"""
        app_font = QFont("Microsoft YaHei", 10)
        QApplication.setFont(app_font)

        self.dark_palette = QPalette()
        self.dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        self.dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        self.dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35)) # For QTextEdit background
        self.dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
        self.dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
        self.dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        self.dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255)) # For QTextEdit text
        self.dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        self.dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        self.dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        self.dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        self.dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

        self.light_palette = QPalette() # Using default Qt light palette by not setting it fully

        self.setPalette(self.light_palette) # Default to light mode

        self.dark_mode_btn = QPushButton("切换深色模式")
        self.dark_mode_btn.clicked.connect(self.toggle_dark_mode)
        self.dark_mode_btn.setCheckable(True)

    def create_top_controls(self, parent_layout):
        """创建顶部控制栏"""
        top_frame = QFrame()
        top_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        top_controls_layout = QHBoxLayout(top_frame)

        load_server_btn = QPushButton("加载服务器根目录")
        load_server_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        load_server_btn.clicked.connect(self.select_server_root_directory)
        top_controls_layout.addWidget(load_server_btn)

        self.server_root_label = QLabel("未加载服务器根目录")
        top_controls_layout.addWidget(self.server_root_label, 1)
        
        quick_access_group = QGroupBox("快速访问")
        quick_access_layout = QHBoxLayout(quick_access_group)

        btn_open_worlds = QPushButton("Worlds")
        btn_open_worlds.clicked.connect(lambda: self.open_server_folder("worlds"))
        quick_access_layout.addWidget(btn_open_worlds)
        self.quick_access_worlds_btn = btn_open_worlds

        btn_open_bp = QPushButton("Behavior Packs")
        btn_open_bp.clicked.connect(lambda: self.open_server_folder("behavior_packs"))
        quick_access_layout.addWidget(btn_open_bp)
        self.quick_access_bp_btn = btn_open_bp

        btn_open_rp = QPushButton("Resource Packs")
        btn_open_rp.clicked.connect(lambda: self.open_server_folder("resource_packs"))
        quick_access_layout.addWidget(btn_open_rp)
        self.quick_access_rp_btn = btn_open_rp
        
        top_controls_layout.addWidget(quick_access_group)

        top_controls_layout.addWidget(self.dark_mode_btn)

        parent_layout.addWidget(top_frame)

    # --- 修改 create_..._section 方法,移除 parent_layout 参数,返回 QGroupBox ---
    def create_world_management_section(self): # 移除 parent_layout
        group = QGroupBox("世界管理")
        layout = QVBoxLayout(group)

        dir_layout = QHBoxLayout()
        self.server_root_display_edit = QLineEdit()
        self.server_root_display_edit.setReadOnly(True)
        dir_layout.addWidget(QLabel("服务器根目录:"))
        dir_layout.addWidget(self.server_root_display_edit)

        self.select_server_root_btn = QPushButton("选择目录")
        self.select_server_root_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.select_server_root_btn.clicked.connect(self.select_server_root_directory)
        dir_layout.addWidget(self.select_server_root_btn)
        layout.addLayout(dir_layout)

        self.worlds_list = QTreeWidget()
        self.worlds_list.setHeaderLabels(["世界名称", "最后修改时间"])
        self.worlds_list.setColumnWidth(0, 200)
        self.worlds_list.setColumnWidth(1, 150)
        self.worlds_list.itemSelectionChanged.connect(self.on_world_select)
        layout.addWidget(self.worlds_list)

        buttons_layout = QHBoxLayout()
        self.load_world_btn = QPushButton("加载选中世界")
        self.load_world_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.load_world_btn.clicked.connect(self.load_selected_world)
        buttons_layout.addWidget(self.load_world_btn)

        self.backup_world_btn = QPushButton("备份选中世界")
        self.backup_world_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.backup_world_btn.clicked.connect(self.backup_selected_world)
        buttons_layout.addWidget(self.backup_world_btn)
        
        self.restore_world_btn = QPushButton("从备份恢复")
        self.restore_world_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        self.restore_world_btn.clicked.connect(self.restore_world_dialog)
        buttons_layout.addWidget(self.restore_world_btn)

        self.edit_world_settings_btn = QPushButton("编辑世界设置")
        self.edit_world_settings_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.edit_world_settings_btn.clicked.connect(self.edit_world_settings)
        buttons_layout.addWidget(self.edit_world_settings_btn)

        layout.addLayout(buttons_layout)
        
        self.load_world_btn.setEnabled(False)
        self.backup_world_btn.setEnabled(False)
        self.restore_world_btn.setEnabled(False)
        self.edit_world_settings_btn.setEnabled(False)
        
        return group


    def create_server_pack_management_section(self):
        group = QGroupBox("服务器包管理")
        layout = QVBoxLayout(group)

        search_sort_layout = QHBoxLayout()
        self.server_pack_search = QLineEdit()
        self.server_pack_search.setPlaceholderText("按名称, UUID, 版本等搜索包...")
        self.server_pack_search.textChanged.connect(self.filter_server_packs)
        search_sort_layout.addWidget(QLabel("搜索:"))
        search_sort_layout.addWidget(self.server_pack_search)

        self.server_pack_sort = QComboBox()
        self.server_pack_sort.addItems(["按名称 (Manifest)", "按文件夹名", "按版本", "按修改时间 (manifest)"]) # Updated sort options
        self.server_pack_sort.currentTextChanged.connect(self.sort_server_packs)
        search_sort_layout.addWidget(QLabel("排序:"))
        search_sort_layout.addWidget(self.server_pack_sort)
        layout.addLayout(search_sort_layout)

        self.server_bp_tree = QTreeWidget()
        # Updated headers for server pack trees
        self.server_bp_tree.setHeaderLabels(["文件夹名", "名称 (Manifest)", "UUID", "版本", "修改日期"])
        self.server_bp_tree.setColumnWidth(0, 150) # Folder Name
        self.server_bp_tree.setColumnWidth(1, 180) # Manifest Name
        self.server_bp_tree.setColumnWidth(2, 220) # UUID
        self.server_bp_tree.setColumnWidth(3, 70)  # Version
        self.server_bp_tree.setColumnWidth(4, 120) # Mod Date
        self.server_bp_tree.itemSelectionChanged.connect(self.on_server_pack_select)
        layout.addWidget(self.server_bp_tree)

        self.server_rp_tree = QTreeWidget()
        self.server_rp_tree.setHeaderLabels(["文件夹名", "名称 (Manifest)", "UUID", "版本", "修改日期"])
        self.server_rp_tree.setColumnWidth(0, 150) # Folder Name
        self.server_rp_tree.setColumnWidth(1, 180) # Manifest Name
        self.server_rp_tree.setColumnWidth(2, 220) # UUID
        self.server_rp_tree.setColumnWidth(3, 70)  # Version
        self.server_rp_tree.setColumnWidth(4, 120) # Mod Date
        self.server_rp_tree.itemSelectionChanged.connect(self.on_server_pack_select)
        layout.addWidget(self.server_rp_tree)

        buttons_layout = QHBoxLayout()
        self.refresh_server_packs_btn = QPushButton("刷新列表")
        self.refresh_server_packs_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))        
        self.refresh_server_packs_btn.clicked.connect(self.refresh_server_packs_list)
        buttons_layout.addWidget(self.refresh_server_packs_btn)

        self.quick_add_server_pack_btn = QPushButton("快速添加选中包到世界")
        self.quick_add_server_pack_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.quick_add_server_pack_btn.clicked.connect(self.quick_add_selected_server_pack_to_world)
        buttons_layout.addWidget(self.quick_add_server_pack_btn)
        layout.addLayout(buttons_layout)

        self.refresh_server_packs_btn.setEnabled(False)
        self.quick_add_server_pack_btn.setEnabled(False)
        
        return group


    def create_server_control_section(self):
        group = QGroupBox("服务器控制台")
        layout = QVBoxLayout(group)

        actions_layout = QHBoxLayout()
        self.start_server_btn = QPushButton("启动服务器")
        self.start_server_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.start_server_btn.clicked.connect(self.start_server)
        actions_layout.addWidget(self.start_server_btn)

        self.stop_server_btn = QPushButton("停止服务器")
        self.stop_server_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_server_btn.clicked.connect(self.stop_server)
        actions_layout.addWidget(self.stop_server_btn)
        
        self.edit_server_properties_btn = QPushButton("编辑 server.properties")
        self.edit_server_properties_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)) 
        self.edit_server_properties_btn.clicked.connect(self.edit_server_properties)
        actions_layout.addWidget(self.edit_server_properties_btn)
        layout.addLayout(actions_layout)

        self.server_log_display = QTextEdit()
        self.server_log_display.setReadOnly(True)
        self.server_log_display.setFont(QFont("Consolas", 9)) 
        layout.addWidget(self.server_log_display)

        command_layout = QHBoxLayout()
        self.server_command_input = QLineEdit()
        self.server_command_input.setPlaceholderText("输入服务器命令 (例如: list, say Hello)...")
        self.server_command_input.returnPressed.connect(self.send_server_command) 
        command_layout.addWidget(self.server_command_input)

        self.send_command_btn = QPushButton("发送")
        self.send_command_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOkButton))
        self.send_command_btn.clicked.connect(self.send_server_command)
        command_layout.addWidget(self.send_command_btn)
        layout.addLayout(command_layout)
        
        self.update_server_controls_state() 
        return group


    def create_pack_import_section(self, parent_layout):
        group_box = QGroupBox("包导入工具")
        layout = QVBoxLayout(group_box)

        import_layout = QHBoxLayout()
        self.import_pack_btn = QPushButton("选择 .mcaddon/.mcpack 导入")
        self.import_pack_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.import_pack_btn.clicked.connect(self.import_pack_dialog)
        import_layout.addWidget(self.import_pack_btn)

        target_layout = QVBoxLayout()
        self.import_target_server_radio = QRadioButton("导入到服务器级文件夹")
        self.import_target_server_radio.setChecked(True)
        self.import_target_server_radio.toggled.connect(self.update_import_options_state)
        target_layout.addWidget(self.import_target_server_radio)

        self.import_target_world_radio = QRadioButton("导入到当前加载的存档")
        self.import_target_world_radio.toggled.connect(self.update_import_options_state)
        target_layout.addWidget(self.import_target_world_radio)
        import_layout.addLayout(target_layout)

        self.import_to_world_subdirs_check = QCheckBox("同时复制包文件到存档文件夹内")
        self.import_to_world_subdirs_check.setChecked(True) 
        import_layout.addWidget(self.import_to_world_subdirs_check)
        layout.addLayout(import_layout)
        parent_layout.addWidget(group_box)

        self.import_pack_btn.setEnabled(False)
        self.import_target_server_radio.setEnabled(False)
        self.import_target_world_radio.setEnabled(False)
        self.import_to_world_subdirs_check.setEnabled(False)

    def create_world_pack_management_section(self, parent_layout):
        splitter = QSplitter(Qt.Orientation.Vertical)

        behavior_group = QGroupBox("行为包 (world_behavior_packs.json)")
        behavior_layout = QVBoxLayout(behavior_group)
        self.behavior_pack_group_box = behavior_group

        file_controls_bp = QHBoxLayout()
        self.world_behavior_save_btn = QPushButton("保存更改")
        self.world_behavior_save_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.world_behavior_save_btn.clicked.connect(lambda: self.save_world_json_file("behavior"))
        file_controls_bp.addWidget(self.world_behavior_save_btn)

        self.world_behavior_file_status = QLabel("JSON未加载")
        file_controls_bp.addWidget(self.world_behavior_file_status, 1)

        self.world_behavior_export_btn = QPushButton("导出配置")
        self.world_behavior_export_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.world_behavior_export_btn.clicked.connect(lambda: self.export_pack_config("behavior"))
        file_controls_bp.addWidget(self.world_behavior_export_btn)

        self.world_behavior_import_btn = QPushButton("导入配置")
        self.world_behavior_import_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.world_behavior_import_btn.clicked.connect(lambda: self.import_pack_config("behavior"))
        file_controls_bp.addWidget(self.world_behavior_import_btn)
        behavior_layout.addLayout(file_controls_bp)

        self.world_behavior_tree = QTreeWidget()
        # Updated headers for world pack trees
        self.world_behavior_tree.setHeaderLabels(["名称 (Manifest)", "Pack ID (UUID)", "版本"])
        self.world_behavior_tree.setColumnWidth(0, 200) # Manifest Name
        self.world_behavior_tree.setColumnWidth(1, 250) # UUID
        self.world_behavior_tree.setColumnWidth(2, 80)  # Version
        self.world_behavior_tree.itemSelectionChanged.connect(lambda: self.on_world_pack_json_entry_select("behavior"))
        behavior_layout.addWidget(self.world_behavior_tree)

        edit_group_bp = QGroupBox("添加/编辑选中条目")
        edit_layout_bp = QVBoxLayout(edit_group_bp)
        id_layout_bp = QHBoxLayout()
        id_layout_bp.addWidget(QLabel("Pack ID (UUID):"))
        self.world_behavior_id_entry = QLineEdit()
        id_layout_bp.addWidget(self.world_behavior_id_entry)
        edit_layout_bp.addLayout(id_layout_bp)
        version_layout_bp = QHBoxLayout()
        version_layout_bp.addWidget(QLabel("版本 (例: 1,0,0):"))
        self.world_behavior_version_entry = QLineEdit()
        version_layout_bp.addWidget(self.world_behavior_version_entry)
        edit_layout_bp.addLayout(version_layout_bp)
        buttons_layout_bp = QHBoxLayout()
        self.world_behavior_add_btn = QPushButton("添加/更新")
        self.world_behavior_add_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.world_behavior_add_btn.clicked.connect(lambda: self.add_pack_entry_to_world_json("behavior"))
        buttons_layout_bp.addWidget(self.world_behavior_add_btn)
        self.world_behavior_remove_btn = QPushButton("移除选中")
        self.world_behavior_remove_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.world_behavior_remove_btn.clicked.connect(lambda: self.remove_pack_entry_from_world_json("behavior"))
        buttons_layout_bp.addWidget(self.world_behavior_remove_btn)
        self.world_behavior_clear_btn = QPushButton("清空输入")
        self.world_behavior_clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        self.world_behavior_clear_btn.clicked.connect(lambda: self.clear_world_pack_json_entry_fields("behavior"))
        buttons_layout_bp.addWidget(self.world_behavior_clear_btn)
        edit_layout_bp.addLayout(buttons_layout_bp)
        behavior_layout.addWidget(edit_group_bp)
        splitter.addWidget(behavior_group)

        resource_group = QGroupBox("资源包 (world_resource_packs.json)")
        resource_layout = QVBoxLayout(resource_group)
        self.resource_pack_group_box = resource_group

        file_controls_rp = QHBoxLayout()
        self.world_resource_save_btn = QPushButton("保存更改")
        self.world_resource_save_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.world_resource_save_btn.clicked.connect(lambda: self.save_world_json_file("resource"))
        file_controls_rp.addWidget(self.world_resource_save_btn)
        self.world_resource_file_status = QLabel("JSON未加载")
        file_controls_rp.addWidget(self.world_resource_file_status, 1)
        self.world_resource_export_btn = QPushButton("导出配置")
        self.world_resource_export_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.world_resource_export_btn.clicked.connect(lambda: self.export_pack_config("resource"))
        file_controls_rp.addWidget(self.world_resource_export_btn)
        self.world_resource_import_btn = QPushButton("导入配置")
        self.world_resource_import_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.world_resource_import_btn.clicked.connect(lambda: self.import_pack_config("resource"))
        file_controls_rp.addWidget(self.world_resource_import_btn)
        resource_layout.addLayout(file_controls_rp)

        self.world_resource_tree = QTreeWidget()
        self.world_resource_tree.setHeaderLabels(["名称 (Manifest)", "Pack ID (UUID)", "版本"])
        self.world_resource_tree.setColumnWidth(0, 200) # Manifest Name
        self.world_resource_tree.setColumnWidth(1, 250) # UUID
        self.world_resource_tree.setColumnWidth(2, 80)  # Version
        self.world_resource_tree.itemSelectionChanged.connect(lambda: self.on_world_pack_json_entry_select("resource"))
        resource_layout.addWidget(self.world_resource_tree)

        edit_group_rp = QGroupBox("添加/编辑选中条目")
        edit_layout_rp = QVBoxLayout(edit_group_rp)
        id_layout_rp = QHBoxLayout()
        id_layout_rp.addWidget(QLabel("Pack ID (UUID):"))
        self.world_resource_id_entry = QLineEdit()
        id_layout_rp.addWidget(self.world_resource_id_entry)
        edit_layout_rp.addLayout(id_layout_rp)
        version_layout_rp = QHBoxLayout()
        version_layout_rp.addWidget(QLabel("版本 (例: 1,0,0):"))
        self.world_resource_version_entry = QLineEdit()
        version_layout_rp.addWidget(self.world_resource_version_entry)
        edit_layout_rp.addLayout(version_layout_rp)
        buttons_layout_rp = QHBoxLayout()
        self.world_resource_add_btn = QPushButton("添加/更新")
        self.world_resource_add_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.world_resource_add_btn.clicked.connect(lambda: self.add_pack_entry_to_world_json("resource"))
        buttons_layout_rp.addWidget(self.world_resource_add_btn)
        self.world_resource_remove_btn = QPushButton("移除选中")
        self.world_resource_remove_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.world_resource_remove_btn.clicked.connect(lambda: self.remove_pack_entry_from_world_json("resource"))
        buttons_layout_rp.addWidget(self.world_resource_remove_btn)
        self.world_resource_clear_btn = QPushButton("清空输入")
        self.world_resource_clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        self.world_resource_clear_btn.clicked.connect(lambda: self.clear_world_pack_json_entry_fields("resource"))
        buttons_layout_rp.addWidget(self.world_resource_clear_btn)
        edit_layout_rp.addLayout(buttons_layout_rp)
        resource_layout.addWidget(edit_group_rp)
        splitter.addWidget(resource_group)
        parent_layout.addWidget(splitter)

        self.world_behavior_save_btn.setEnabled(False)
        self.world_resource_save_btn.setEnabled(False)
        self.world_behavior_export_btn.setEnabled(False)
        self.world_behavior_import_btn.setEnabled(False)
        self.world_resource_export_btn.setEnabled(False)
        self.world_resource_import_btn.setEnabled(False)


    def update_status(self, message, level="info"):
        color_map = {
            "info": "black" if not self.dark_mode_btn.isChecked() else "white",
            "warning": "darkorange",
            "error": "red",
            "success": "green"
        }
        color = color_map.get(level.lower(), "black" if not self.dark_mode_btn.isChecked() else "white")
        
        if self.dark_mode_btn.isChecked() and color == "black":
            color = "lightgray"

        self.status_bar.showMessage(message)
        self.status_bar.setStyleSheet(f"color: {color};")

    def select_server_root_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择服务器根目录", "", QFileDialog.Option.ShowDirsOnly)
        if dir_path:
            self.server_root_path = dir_path
            self.server_root_display_edit.setText(dir_path) 
            self.server_root_label.setText(f"服务器根目录: {dir_path}")
            self.update_status(f"已加载服务器根目录: {dir_path}", "success")

            self.refresh_worlds_list()
            self.refresh_server_packs_list() # This will also populate server_pack_uuid_to_manifest_details
            self.enable_server_specific_controls()
            
            self.reset_world_specific_ui()
            self.disable_all_world_specific_controls()

            are_quick_access_buttons_enabled = bool(self.server_root_path)
            self.quick_access_worlds_btn.setEnabled(are_quick_access_buttons_enabled)
            self.quick_access_bp_btn.setEnabled(are_quick_access_buttons_enabled)
            self.quick_access_rp_btn.setEnabled(are_quick_access_buttons_enabled)


    def reset_world_specific_ui(self):
        self.loaded_world_name = ""
        self.loaded_world_path = ""
        self.world_behavior_packs_data = []
        self.world_resource_packs_data = []
        self.world_behavior_json_path = ""
        self.world_resource_json_path = ""

        self.world_behavior_tree.clear()
        self.world_resource_tree.clear()
        self.world_behavior_file_status.setText("JSON未加载")
        self.world_resource_file_status.setText("JSON未加载")
        self.behavior_pack_group_box.setTitle("行为包 (未加载存档 - world_behavior_packs.json)")
        self.resource_pack_group_box.setTitle("资源包 (未加载存档 - world_resource_packs.json)")
        
        self.clear_world_pack_json_entry_fields("behavior")
        self.clear_world_pack_json_entry_fields("resource")


    def refresh_worlds_list(self):
        self.worlds_list.clear()
        self.on_world_select() 

        if not self.server_root_path:
            return

        worlds_dir = os.path.join(self.server_root_path, "worlds")
        if not os.path.exists(worlds_dir):
            self.update_status("未找到 'worlds' 目录", "warning")
            self.restore_world_btn.setEnabled(False)
            return
        
        self.restore_world_btn.setEnabled(True)

        world_count = 0
        for world_name in os.listdir(worlds_dir):
            world_path = os.path.join(worlds_dir, world_name)
            if os.path.isdir(world_path):
                if not (os.path.exists(os.path.join(world_path, "levelname.txt")) or \
                        os.path.exists(os.path.join(world_path, "level.dat"))):
                    continue 

                mtime = os.path.getmtime(world_path)
                mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                item = QTreeWidgetItem([world_name, mtime_str])
                self.worlds_list.addTopLevelItem(item)
                world_count += 1
        self.update_status(f"已刷新世界列表, 共 {world_count} 个世界", "info")


    def on_world_select(self):
        selected_items = self.worlds_list.selectedItems()
        has_selection = len(selected_items) > 0

        self.load_world_btn.setEnabled(has_selection)
        self.backup_world_btn.setEnabled(has_selection)
        self.edit_world_settings_btn.setEnabled(has_selection and bool(self.loaded_world_name) and self.loaded_world_name == selected_items[0].text(0) if has_selection else False)


    def load_selected_world(self):
        selected_items = self.worlds_list.selectedItems()
        if not selected_items:
            return

        world_name = selected_items[0].text(0)
        world_path = os.path.join(self.server_root_path, "worlds", world_name)

        if not os.path.exists(world_path):
            QMessageBox.critical(self, "错误", f"世界目录不存在: {world_path}")
            return

        self.loaded_world_name = world_name
        self.loaded_world_path = world_path
        
        self.behavior_pack_group_box.setTitle(f"行为包 ({world_name} - world_behavior_packs.json)")
        self.resource_pack_group_box.setTitle(f"资源包 ({world_name} - world_resource_packs.json)")

        self.world_behavior_json_path = os.path.join(world_path, "world_behavior_packs.json")
        self.world_resource_json_path = os.path.join(world_path, "world_resource_packs.json")

        self.world_behavior_packs_data = [] 
        if os.path.exists(self.world_behavior_json_path):
            try:
                with open(self.world_behavior_json_path, 'r', encoding='utf-8') as f:
                    self.world_behavior_packs_data = json.load(f)
                self.world_behavior_file_status.setText("JSON已加载")
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "警告", f"加载行为包JSON失败: {str(e)}\n文件可能已损坏.将使用空列表.")
                self.world_behavior_file_status.setText(f"JSON加载失败: {e}")
            except Exception as e:
                QMessageBox.warning(self, "警告", f"加载行为包JSON时发生未知错误: {str(e)}")
                self.world_behavior_file_status.setText(f"JSON加载错误: {e}")
        else:
            self.world_behavior_file_status.setText("JSON不存在 (将创建)")
        self.refresh_world_packs_tree("behavior")


        self.world_resource_packs_data = []
        if os.path.exists(self.world_resource_json_path):
            try:
                with open(self.world_resource_json_path, 'r', encoding='utf-8') as f:
                    self.world_resource_packs_data = json.load(f)
                self.world_resource_file_status.setText("JSON已加载")
            except json.JSONDecodeError as e:
                QMessageBox.warning(self, "警告", f"加载资源包JSON失败: {str(e)}\n文件可能已损坏.将使用空列表.")
                self.world_resource_file_status.setText(f"JSON加载失败: {e}")
            except Exception as e:
                QMessageBox.warning(self, "警告", f"加载资源包JSON时发生未知错误: {str(e)}")
                self.world_resource_file_status.setText(f"JSON加载错误: {e}")
        else:
            self.world_resource_file_status.setText("JSON不存在 (将创建)")
        self.refresh_world_packs_tree("resource")

        self.enable_all_world_specific_controls()
        self.update_status(f"已加载世界: {world_name}", "success")
        self.on_world_select()

    def backup_selected_world(self):
        selected_items = self.worlds_list.selectedItems()
        if not selected_items:
            return

        world_name = selected_items[0].text(0)

        if not self.server_root_path:
            QMessageBox.warning(self, "错误", "服务器根目录未设置,无法备份.")
            return
        
        world_path = os.path.join(self.server_root_path, "worlds", world_name)

        if not os.path.exists(world_path):
            QMessageBox.critical(self, "错误", f"世界目录不存在: {world_path}")
            return

        backup_dir = os.path.join(self.server_root_path, "world_backups")
        try:
            os.makedirs(backup_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建备份目录失败: {str(e)}")
            return

        backup_name_base = f"{world_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_type, ok = QInputDialog.getItem(self, "选择备份类型", "请选择备份方式:", ["文件夹复制", "ZIP压缩包"], 0, False)
        if not ok:
            return

        if backup_type == "文件夹复制":
            backup_path = os.path.join(backup_dir, backup_name_base)
            try:
                shutil.copytree(world_path, backup_path)
                self.update_status(f"已创建世界备份 (文件夹): {backup_name_base}", "success")
                QMessageBox.information(self, "成功", f"文件夹备份 '{backup_name_base}' 创建成功!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"备份世界 (文件夹) 失败: {str(e)}")
        
        elif backup_type == "ZIP压缩包":
            backup_zip_path = os.path.join(backup_dir, f"{backup_name_base}.zip")
            try:
                with zipfile.ZipFile(backup_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, _, files in os.walk(world_path):
                        for file in files:
                            file_full_path = os.path.join(root, file)
                            archive_name = os.path.relpath(file_full_path, world_path)
                            zipf.write(file_full_path, archive_name)
                self.update_status(f"已创建世界备份 (ZIP): {backup_name_base}.zip", "success")
                QMessageBox.information(self, "成功", f"ZIP备份 '{backup_name_base}.zip' 创建成功!")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"备份世界 (ZIP) 失败: {str(e)}")


    def restore_world_dialog(self):
        if not self.server_root_path:
            QMessageBox.warning(self, "警告", "请先加载服务器根目录.")
            return
            
        selected_items = self.worlds_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先在左侧世界列表中选择要恢复到的目标世界.")
            return
        target_world_name = selected_items[0].text(0)

        backup_dir = os.path.join(self.server_root_path, "world_backups")
        if not os.path.exists(backup_dir) or not os.listdir(backup_dir):
            QMessageBox.information(self, "提示", "没有找到 'world_backups' 目录或备份为空.")
            return

        backups = []
        for f_name in os.listdir(backup_dir):
            if f_name.startswith(target_world_name + "_backup_") and \
               (os.path.isdir(os.path.join(backup_dir, f_name)) or f_name.endswith(".zip")):
                backups.append(f_name)
        
        if not backups:
            QMessageBox.information(self, "提示", f"没有找到 '{target_world_name}' 的可用备份.")
            return

        backups.sort(reverse=True) 
        backup_to_restore, ok = QInputDialog.getItem(self, "选择要恢复的备份", f"恢复到世界 '{target_world_name}':", backups, 0, False)

        if ok and backup_to_restore:
            self.restore_world(target_world_name, backup_to_restore, backup_dir)

    def restore_world(self, world_name, backup_name, backup_dir_path):
        target_world_path = os.path.join(self.server_root_path, "worlds", world_name)
        source_backup_path = os.path.join(backup_dir_path, backup_name)

        if not os.path.exists(source_backup_path):
            QMessageBox.critical(self, "错误", f"备份源不存在: {source_backup_path}")
            return

        reply = QMessageBox.warning(self, "确认恢复",
                                   f"确定要用备份 '{backup_name}' 覆盖世界 '{world_name}' 吗?\n当前世界 '{world_name}' 的内容将被删除!",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        try:
            if os.path.exists(target_world_path):
                shutil.rmtree(target_world_path)
            
            if os.path.isdir(source_backup_path): 
                shutil.copytree(source_backup_path, target_world_path)
                self.update_status(f"已从文件夹备份恢复世界: {world_name}", "success")
            elif backup_name.endswith(".zip"): 
                os.makedirs(target_world_path, exist_ok=True)
                with zipfile.ZipFile(source_backup_path, 'r') as zip_ref:
                    zip_ref.extractall(target_world_path)
                self.update_status(f"已从ZIP备份恢复世界: {world_name}", "success")
            else:
                QMessageBox.critical(self, "错误", f"未知的备份格式: {backup_name}")
                return

            self.refresh_worlds_list()
            if self.loaded_world_name == world_name: 
                self.load_selected_world() 
        except Exception as e:
            QMessageBox.critical(self, "错误", f"恢复世界失败: {str(e)}")


    def enable_server_specific_controls(self):
        is_root_loaded = bool(self.server_root_path)
        self.import_pack_btn.setEnabled(is_root_loaded)
        self.import_target_server_radio.setEnabled(is_root_loaded)
        self.refresh_server_packs_btn.setEnabled(is_root_loaded)
        self.restore_world_btn.setEnabled(is_root_loaded and os.path.exists(os.path.join(self.server_root_path, "worlds")))

        self.edit_server_properties_btn.setEnabled(is_root_loaded)
        self.update_server_controls_state()

        self.quick_access_worlds_btn.setEnabled(is_root_loaded)
        self.quick_access_bp_btn.setEnabled(is_root_loaded)
        self.quick_access_rp_btn.setEnabled(is_root_loaded)

    def disable_server_specific_controls(self):
        self.import_pack_btn.setEnabled(False)
        self.import_target_server_radio.setEnabled(False)
        self.refresh_server_packs_btn.setEnabled(False)
        self.restore_world_btn.setEnabled(False)
        
        self.edit_server_properties_btn.setEnabled(False)
        self.update_server_controls_state() 

        self.quick_access_worlds_btn.setEnabled(False)
        self.quick_access_bp_btn.setEnabled(False)
        self.quick_access_rp_btn.setEnabled(False)


    def enable_all_world_specific_controls(self):
        is_world_loaded = bool(self.loaded_world_name)
        self.import_target_world_radio.setEnabled(is_world_loaded)
        self.update_import_options_state()

        for pack_type in ["behavior", "resource"]:
            id_entry = getattr(self, f"world_{pack_type}_id_entry")
            version_entry = getattr(self, f"world_{pack_type}_version_entry")
            add_btn = getattr(self, f"world_{pack_type}_add_btn")
            clear_btn = getattr(self, f"world_{pack_type}_clear_btn")
            save_btn = getattr(self, f"world_{pack_type}_save_btn")
            export_btn = getattr(self, f"world_{pack_type}_export_btn")
            import_btn = getattr(self, f"world_{pack_type}_import_btn")

            id_entry.setEnabled(is_world_loaded)
            version_entry.setEnabled(is_world_loaded)
            add_btn.setEnabled(is_world_loaded)
            clear_btn.setEnabled(is_world_loaded)
            save_btn.setEnabled(is_world_loaded)
            export_btn.setEnabled(is_world_loaded)
            import_btn.setEnabled(is_world_loaded)
        
        self.quick_add_server_pack_btn.setEnabled(is_world_loaded and (len(self.server_bp_tree.selectedItems()) > 0 or len(self.server_rp_tree.selectedItems()) > 0))
        self.on_world_pack_json_entry_select("behavior") 
        self.on_world_pack_json_entry_select("resource")


    def disable_all_world_specific_controls(self):
        self.import_target_world_radio.setEnabled(False)
        self.import_to_world_subdirs_check.setEnabled(False) 
        self.quick_add_server_pack_btn.setEnabled(False)
        self.edit_world_settings_btn.setEnabled(False)


        for pack_type in ["behavior", "resource"]:
            getattr(self, f"world_{pack_type}_id_entry").setEnabled(False)
            getattr(self, f"world_{pack_type}_version_entry").setEnabled(False)
            getattr(self, f"world_{pack_type}_add_btn").setEnabled(False)
            getattr(self, f"world_{pack_type}_remove_btn").setEnabled(False)
            getattr(self, f"world_{pack_type}_clear_btn").setEnabled(False)
            getattr(self, f"world_{pack_type}_save_btn").setEnabled(False)
            getattr(self, f"world_{pack_type}_export_btn").setEnabled(False)
            getattr(self, f"world_{pack_type}_import_btn").setEnabled(False)


    def refresh_server_packs_list(self):
        self.server_bp_tree.clear()
        self.server_rp_tree.clear()
        self.server_pack_uuid_to_manifest_details.clear() # Clear the map before repopulating
        self.on_server_pack_select()

        if not self.server_root_path:
            return

        pack_dirs = {
            "behavior": os.path.join(self.server_root_path, "behavior_packs"),
            "resource": os.path.join(self.server_root_path, "resource_packs")
        }
        trees = {"behavior": self.server_bp_tree, "resource": self.server_rp_tree}

        for pack_type, pack_dir_path in pack_dirs.items():
            tree = trees[pack_type]
            if os.path.exists(pack_dir_path):
                for pack_folder_name in os.listdir(pack_dir_path): # pack_folder_name is the directory name
                    pack_path = os.path.join(pack_dir_path, pack_folder_name)
                    if os.path.isdir(pack_path):
                        manifest_path = os.path.join(pack_path, "manifest.json")
                        mod_time_str = ""
                        manifest_name_str = "N/A"
                        uuid_str = "N/A"
                        version_str_display = "N/A"
                        version_list = [0,0,0]

                        if os.path.exists(manifest_path):
                            try:
                                with open(manifest_path, 'r', encoding='utf-8') as f:
                                    manifest = json.load(f)
                                header = manifest.get("header", {})
                                manifest_name_str = header.get("name", "N/A")
                                # Attempt to decode if it's a pack name string like "pack.name"
                                if manifest_name_str.startswith("pack.") or manifest_name_str.startswith("resourcePack.") or manifest_name_str.startswith("behaviorPack.") :
                                    # Look for texts/en_US.lang (or other lang)
                                    lang_path_us = os.path.join(pack_path, "texts", "en_US.lang")
                                    # lang_path_cn = os.path.join(pack_path, "texts", "zh_CN.lang") # Example for Chinese
                                    # selected_lang_path = lang_path_cn if os.path.exists(lang_path_cn) else lang_path_us
                                    selected_lang_path = lang_path_us # Default to en_US for simplicity

                                    if os.path.exists(selected_lang_path):
                                        try:
                                            with open(selected_lang_path, 'r', encoding='utf-8') as lang_f:
                                                for line in lang_f:
                                                    if '=' in line:
                                                        key, value = line.split('=', 1)
                                                        if key.strip() == manifest_name_str:
                                                            manifest_name_str = value.strip()
                                                            break
                                        except Exception:
                                            pass # Keep original manifest_name_str if lang file parsing fails

                                uuid_str = header.get("uuid", "N/A")
                                version_list = header.get("version", [0,0,0])
                                if isinstance(version_list, list) and len(version_list) > 0:
                                     version_str_display = '.'.join(map(str, version_list))
                                else:
                                     version_list = [0,0,0] # ensure it's a list for storing
                                     version_str_display = "0.0.0"

                                mod_time = os.path.getmtime(manifest_path)
                                mod_time_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M")

                                if uuid_str != "N/A":
                                    self.server_pack_uuid_to_manifest_details[uuid_str] = {
                                        "name": manifest_name_str,
                                        "version_list": version_list,
                                        "type": pack_type,
                                        "folder_name": pack_folder_name
                                    }
                            except Exception as e:
                                self.update_status(f"读取 {pack_folder_name} manifest.json 失败: {e}", "warning")
                        
                        # Columns: Folder Name, Manifest Name, UUID, Version, Mod Date
                        item = QTreeWidgetItem([pack_folder_name, manifest_name_str, uuid_str, version_str_display, mod_time_str])
                        item.setData(0, Qt.ItemDataRole.UserRole, os.path.getmtime(pack_path)) 
                        if mod_time_str: 
                             item.setData(4, Qt.ItemDataRole.UserRole, mod_time) # For sorting by manifest mod time (col 4)
                        tree.addTopLevelItem(item)
            
        self.filter_server_packs() 
        self.sort_server_packs() 
        self.update_status("已刷新服务器包列表", "info")
        # After refreshing server packs, also refresh world packs if a world is loaded,
        # as the names might have updated.
        if self.loaded_world_name:
            self.refresh_world_packs_tree("behavior")
            self.refresh_world_packs_tree("resource")


    def on_server_pack_select(self):
        bp_selected = len(self.server_bp_tree.selectedItems()) > 0
        rp_selected = len(self.server_rp_tree.selectedItems()) > 0
        has_selection = bp_selected or rp_selected
        
        self.quick_add_server_pack_btn.setEnabled(has_selection and bool(self.loaded_world_name))


    def quick_add_selected_server_pack_to_world(self):
        if not self.loaded_world_name:
            QMessageBox.warning(self, "警告", "请先加载一个世界.")
            return

        selected_item = None
        pack_type = None

        if self.server_bp_tree.selectedItems():
            selected_item = self.server_bp_tree.selectedItems()[0]
            pack_type = "behavior"
        elif self.server_rp_tree.selectedItems():
            selected_item = self.server_rp_tree.selectedItems()[0]
            pack_type = "resource"
        
        if not selected_item or not pack_type:
            QMessageBox.warning(self, "警告", "请在服务器包列表中选择一个包.")
            return

        # Column indices: 0:Folder, 1:ManifestName, 2:UUID, 3:Version, 4:ModDate
        pack_id = selected_item.text(2) # UUID
        version_str_display = selected_item.text(3) # Version string e.g., "1.0.0"
        
        if pack_id == "N/A" or version_str_display == "N/A":
            QMessageBox.warning(self, "警告", "选中的包缺少有效的 UUID 或版本信息.")
            return

        try:
            version_list = [int(v) for v in version_str_display.split('.')]
            if len(version_list) != 3: # Should be already handled by manifest reading, but good check
                raise ValueError("版本号必须是三段式,如 1.0.0")
        except ValueError as e:
            QMessageBox.warning(self, "警告", f"包版本格式无效: {version_str_display}. 错误: {e}")
            return

        data_list = self.world_behavior_packs_data if pack_type == "behavior" else self.world_resource_packs_data
        
        for entry in data_list:
            if entry.get("pack_id") == pack_id:
                reply = QMessageBox.question(self, "确认", f"ID为 '{pack_id}' 的包已存在于世界配置中.\n是否要用版本 {version_str_display} 更新它?",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.Yes:
                    entry["version"] = version_list
                    self.save_world_json_file(pack_type) 
                    self.refresh_world_packs_tree(pack_type)
                    self.update_status(f"{pack_type.capitalize()}包 '{pack_id}' 版本已更新.", "success")
                return 

        new_entry = {"pack_id": pack_id, "version": version_list}
        data_list.append(new_entry)
        self.save_world_json_file(pack_type) 
        self.refresh_world_packs_tree(pack_type)
        self.update_status(f"已添加 {pack_type} 包 '{pack_id}' 到世界.", "success")


    def import_pack_dialog(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择要导入的包文件 (.mcpack, .mcaddon)",
            self.server_root_path, 
            "Minecraft 包文件 (*.mcpack *.mcaddon);;所有文件 (*.*)"
        )
        
        if file_paths:
            imported_count = 0
            failed_count = 0
            for file_path in file_paths:
                if self.import_pack(file_path):
                    imported_count +=1
                else:
                    failed_count +=1
            
            summary_message = f"导入完成: {imported_count} 个成功"
            if failed_count > 0:
                summary_message += f", {failed_count} 个失败."
            else:
                summary_message += "."
            self.update_status(summary_message, "info" if failed_count == 0 else "warning")
            self.refresh_server_packs_list() # This will update UUID map and refresh world trees if loaded


    def import_pack(self, file_path):
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "错误", f"文件不存在: {file_path}")
            return False

        file_extension = os.path.splitext(file_path)[1].lower()
        is_mcaddon = file_extension == ".mcaddon"
        
        temp_dir_outer = tempfile.mkdtemp()
        successful_extraction_overall = False
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir_outer)
            
            packs_to_process_paths = [] # Store paths to actual pack content directories
            temp_dirs_to_clean = [] # Store paths of temporary directories created for inner mcpacks

            if is_mcaddon:
                for item_name in os.listdir(temp_dir_outer):
                    item_path = os.path.join(temp_dir_outer, item_name)
                    if item_name.lower().endswith(".mcpack") and os.path.isfile(item_path):
                        temp_dir_inner_mcpack = tempfile.mkdtemp()
                        temp_dirs_to_clean.append(temp_dir_inner_mcpack)
                        with zipfile.ZipFile(item_path, 'r') as inner_zip_ref:
                            inner_zip_ref.extractall(temp_dir_inner_mcpack)
                        # The content of inner_mcpack might be directly the pack, or a folder containing the pack
                        # Check if manifest.json is in temp_dir_inner_mcpack directly
                        if os.path.exists(os.path.join(temp_dir_inner_mcpack, "manifest.json")):
                            packs_to_process_paths.append(temp_dir_inner_mcpack)
                        else: # manifest might be in a subfolder
                            for sub_item_name in os.listdir(temp_dir_inner_mcpack):
                                sub_item_path = os.path.join(temp_dir_inner_mcpack, sub_item_name)
                                if os.path.isdir(sub_item_path) and os.path.exists(os.path.join(sub_item_path, "manifest.json")):
                                    packs_to_process_paths.append(sub_item_path)
                                    break # Assuming one pack per mcpack file

                    elif os.path.isdir(item_path): 
                        if os.path.exists(os.path.join(item_path, "manifest.json")):
                             packs_to_process_paths.append(item_path) 
            else: # It's an mcpack
                # Check if manifest.json is in temp_dir_outer directly
                if os.path.exists(os.path.join(temp_dir_outer, "manifest.json")):
                     packs_to_process_paths.append(temp_dir_outer)
                else: # manifest might be in a subfolder
                    for sub_item_name in os.listdir(temp_dir_outer):
                        sub_item_path = os.path.join(temp_dir_outer, sub_item_name)
                        if os.path.isdir(sub_item_path) and os.path.exists(os.path.join(sub_item_path, "manifest.json")):
                            packs_to_process_paths.append(sub_item_path)
                            break # Assuming one pack per mcpack file


            if not packs_to_process_paths:
                QMessageBox.warning(self, "警告", f"文件 '{os.path.basename(file_path)}' 中未找到有效的包内容.")
                return False

            for extracted_pack_content_path in packs_to_process_paths:
                manifest_path = os.path.join(extracted_pack_content_path, "manifest.json")
                # Already checked existence, but double check doesn't hurt if logic changes
                if not os.path.exists(manifest_path):
                    self.update_status(f"跳过无效包 (无 manifest.json): {os.path.basename(extracted_pack_content_path)}", "warning")
                    continue

                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                
                module_type = "unknown"
                if "modules" in manifest and manifest["modules"]:
                    module_type_from_manifest = manifest["modules"][0].get("type", "unknown").lower()
                    if module_type_from_manifest == "data": 
                        module_type = "behavior"
                    elif module_type_from_manifest == "resources": 
                        module_type = "resource"
                    elif module_type_from_manifest == "script": # Script packs are often behavior packs
                        module_type = "behavior" 


                if module_type == "unknown":
                    pack_folder_basename = os.path.basename(extracted_pack_content_path).lower()
                    if "behavior" in pack_folder_basename or "bp" in pack_folder_basename:
                        module_type = "behavior"
                    elif "resource" in pack_folder_basename or "rp" in pack_folder_basename:
                        module_type = "resource"
                    else:
                        QMessageBox.warning(self, "导入错误", f"无法确定包类型 (行为包/资源包) 从 manifest.json: {os.path.basename(extracted_pack_content_path)}")
                        continue 

                # Use the name of the folder containing manifest.json as the pack_folder_name for destination
                pack_folder_name_for_dest = os.path.basename(extracted_pack_content_path)

                target_base_dir_server = os.path.join(self.server_root_path, f"{module_type}_packs")
                final_pack_dir_server = os.path.join(target_base_dir_server, pack_folder_name_for_dest)

                os.makedirs(target_base_dir_server, exist_ok=True)
                if os.path.exists(final_pack_dir_server):
                    shutil.rmtree(final_pack_dir_server)
                shutil.copytree(extracted_pack_content_path, final_pack_dir_server) # Copy the content path
                self.update_status(f"包 '{pack_folder_name_for_dest}' 已导入到服务器.", "info")
                successful_extraction_overall = True


                if self.import_target_world_radio.isChecked() and self.loaded_world_name and self.import_to_world_subdirs_check.isChecked():
                    target_base_dir_world = os.path.join(self.loaded_world_path, f"{module_type}_packs") # e.g. worlds/MyWorld/behavior_packs
                    final_pack_dir_world = os.path.join(target_base_dir_world, pack_folder_name_for_dest)
                    os.makedirs(target_base_dir_world, exist_ok=True)
                    if os.path.exists(final_pack_dir_world):
                        shutil.rmtree(final_pack_dir_world)
                    shutil.copytree(extracted_pack_content_path, final_pack_dir_world)
                    self.update_status(f"包 '{pack_folder_name_for_dest}' 也已复制到世界 '{self.loaded_world_name}'.", "info")
            
        except zipfile.BadZipFile:
            QMessageBox.critical(self, "错误", f"导入包失败: '{os.path.basename(file_path)}' 不是有效的ZIP/包文件.")
            return False
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入包 '{os.path.basename(file_path)}' 失败: {str(e)}")
            return False
        finally:
            shutil.rmtree(temp_dir_outer, ignore_errors=True) 
            if 'temp_dirs_to_clean' in locals():
                for temp_dir in temp_dirs_to_clean:
                    shutil.rmtree(temp_dir, ignore_errors=True)
        
        return successful_extraction_overall


    def update_import_options_state(self):
        is_world_target = self.import_target_world_radio.isChecked()
        is_world_loaded = bool(self.loaded_world_name)
        
        self.import_to_world_subdirs_check.setEnabled(is_world_target and is_world_loaded)
        if not (is_world_target and is_world_loaded):
            self.import_to_world_subdirs_check.setChecked(False) 
        else:
            # Keep previous state if conditions are met, or default to True
            # self.import_to_world_subdirs_check.setChecked(True) # Re-evaluate if this should always be true
            pass


    def refresh_world_packs_tree(self, pack_type):
        tree = getattr(self, f"world_{pack_type}_tree")
        data = getattr(self, f"world_{pack_type}_packs_data")
        tree.clear()

        if not isinstance(data, list): 
            self.update_status(f"世界{pack_type}包数据格式错误 (不是列表),已清空.", "error")
            setattr(self, f"world_{pack_type}_packs_data", []) 
            data = []

        for entry in data:
            if not isinstance(entry, dict): continue 
            pack_id = entry.get("pack_id", "N/A")
            version_list = entry.get("version", [0,0,0])
            if not isinstance(version_list, list) or not all(isinstance(v, int) for v in version_list):
                version_list = [0,0,0] 
            version_str = '.'.join(map(str, version_list))
            
            # Get pack name from the map
            manifest_details = self.server_pack_uuid_to_manifest_details.get(pack_id)
            pack_display_name = "N/A"
            if manifest_details:
                pack_display_name = manifest_details["name"]
            elif pack_id != "N/A":
                 pack_display_name = f"未知 (ID: {pack_id[:8]}...)"


            # Columns: Manifest Name, Pack ID (UUID), Version
            item = QTreeWidgetItem([pack_display_name, pack_id, version_str])
            tree.addTopLevelItem(item)
        self.update_status(f"已刷新世界 {pack_type} 包列表", "info")
        self.on_world_pack_json_entry_select(pack_type)


    def on_world_pack_json_entry_select(self, pack_type):
        tree = getattr(self, f"world_{pack_type}_tree")
        id_entry = getattr(self, f"world_{pack_type}_id_entry")
        version_entry = getattr(self, f"world_{pack_type}_version_entry")
        remove_btn = getattr(self, f"world_{pack_type}_remove_btn")

        selected_items = tree.selectedItems()
        has_selection = len(selected_items) > 0
        
        remove_btn.setEnabled(has_selection and bool(self.loaded_world_name))

        if has_selection:
            item = selected_items[0]
            # Columns: 0:Manifest Name, 1:UUID, 2:Version
            id_entry.setText(item.text(1)) # UUID from column 1
            version_entry.setText(item.text(2).replace('.',',')) # Version from column 2
        


    def add_pack_entry_to_world_json(self, pack_type):
        if not self.loaded_world_name:
            QMessageBox.warning(self, "警告", "请先加载一个世界.")
            return

        id_entry = getattr(self, f"world_{pack_type}_id_entry")
        version_entry = getattr(self, f"world_{pack_type}_version_entry")
        data_list = getattr(self, f"world_{pack_type}_packs_data")

        pack_id = id_entry.text().strip()
        version_str_input = version_entry.text().strip() 

        if not pack_id:
            QMessageBox.warning(self, "警告", "请输入Pack ID (UUID).")
            return
        try:
            uuid.UUID(pack_id)
        except ValueError:
            QMessageBox.warning(self, "警告", "Pack ID (UUID) 格式无效.")
            return

        if not version_str_input:
            QMessageBox.warning(self, "警告", "请输入版本号.")
            return
        try:
            version_parts = [int(x.strip()) for x in version_str_input.split(',')]
            if len(version_parts) != 3:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "警告", "版本格式无效.请使用三个逗号分隔的数字 (例如: 1,0,0).")
            return

        updated = False
        for i, entry in enumerate(data_list):
            if entry.get("pack_id") == pack_id:
                data_list[i]["version"] = version_parts
                updated = True
                break
        
        if not updated:
            data_list.append({"pack_id": pack_id, "version": version_parts})

        self.save_world_json_file(pack_type) 
        self.refresh_world_packs_tree(pack_type)
        self.update_status(f"世界 {pack_type} 包列表已{'更新' if updated else '添加'}.", "success")


    def remove_pack_entry_from_world_json(self, pack_type):
        if not self.loaded_world_name:
            QMessageBox.warning(self, "警告", "请先加载一个世界.")
            return

        tree = getattr(self, f"world_{pack_type}_tree")
        data_list = getattr(self, f"world_{pack_type}_packs_data")
        
        selected_items = tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请先选择要移除的包条目.")
            return
        
        pack_id_to_remove = selected_items[0].text(1) # UUID is in column 1

        reply = QMessageBox.question(self, "确认移除", f"确定要从世界配置中移除 {pack_type} 包 '{pack_id_to_remove}' 吗?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            original_len = len(data_list)
            setattr(self, f"world_{pack_type}_packs_data", [entry for entry in data_list if entry.get("pack_id") != pack_id_to_remove])
            
            if len(getattr(self, f"world_{pack_type}_packs_data")) < original_len :
                self.save_world_json_file(pack_type) 
                self.refresh_world_packs_tree(pack_type)
                self.update_status(f"已从世界配置中移除 {pack_type} 包 '{pack_id_to_remove}'.", "success")
                self.clear_world_pack_json_entry_fields(pack_type) 
            else:
                self.update_status(f"未找到要移除的 {pack_type} 包 '{pack_id_to_remove}'.", "warning")


    def clear_world_pack_json_entry_fields(self, pack_type):
        getattr(self, f"world_{pack_type}_id_entry").clear()
        getattr(self, f"world_{pack_type}_version_entry").clear()
        getattr(self, f"world_{pack_type}_tree").clearSelection()


    def save_world_json_file(self, pack_type):
        if not self.loaded_world_name:
            QMessageBox.warning(self, "警告", "没有加载世界,无法保存.")
            return

        data = getattr(self, f"world_{pack_type}_packs_data")
        json_path = getattr(self, f"world_{pack_type}_json_path")

        if not json_path: 
            QMessageBox.critical(self, "错误", f"未找到 {pack_type} JSON 路径.")
            return

        try:
            os.makedirs(os.path.dirname(json_path), exist_ok=True)
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False) 
            self.update_status(f"世界 {pack_type} 包JSON文件已保存.", "success")
            file_status_label = getattr(self, f"world_{pack_type}_file_status")
            if file_status_label.text() != "JSON已加载":
                 file_status_label.setText("JSON已加载")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存世界 {pack_type} 包JSON失败: {str(e)}")


    def filter_server_packs(self):
        search_text = self.server_pack_search.text().lower()
        for tree in [self.server_bp_tree, self.server_rp_tree]:
            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                # Search in FolderName (0), ManifestName (1), UUID (2), Version (3)
                match = any(search_text in item.text(col).lower() for col in range(4))
                item.setHidden(not match)

    def sort_server_packs(self):
        sort_option = self.server_pack_sort.currentText()
        
        for tree in [self.server_bp_tree, self.server_rp_tree]:
            sort_column = 0 
            # Columns: 0:Folder, 1:ManifestName, 2:UUID, 3:Version, 4:ModDate
            if sort_option == "按名称 (Manifest)":
                sort_column = 1 
            elif sort_option == "按文件夹名":
                sort_column = 0
            elif sort_option == "按版本":
                sort_column = 3
                def version_key(item_text):
                    try:
                        return [int(p) for p in item_text.split('.')]
                    except:
                        return [0,0,0] 
                key_func = lambda item: version_key(item.text(sort_column))
            elif sort_option == "按修改时间 (manifest)":
                sort_column = 4 # UserRole data for manifest mod time is on col 4
                key_func = lambda item: item.data(sort_column, Qt.ItemDataRole.UserRole) or 0 
            else: # Default or fallback (should not happen with QComboBox)
                key_func = lambda item: item.text(sort_column).lower()

            if sort_option not in ["按版本", "按修改时间 (manifest)"]: 
                tree.sortItems(sort_column, Qt.SortOrder.AscendingOrder)
            else: 
                items = []
                for i in range(tree.topLevelItemCount()):
                    items.append(tree.takeTopLevelItem(0)) 
                
                items.sort(key=key_func)
                
                for item in items: 
                    tree.addTopLevelItem(item)
    
    def edit_world_settings(self):
        if not self.loaded_world_name:
            QMessageBox.warning(self, "警告", "请先加载一个世界.")
            return

        target_file_path = os.path.join(self.loaded_world_path, "levelname.txt")
        file_description = "levelname.txt"

        if not os.path.exists(target_file_path):
            QMessageBox.information(self, "信息", f"文件 '{file_description}' 在世界目录中未找到.")
            reply = QMessageBox.question(self, "创建文件?", 
                                       f"文件 '{file_description}' 未找到.\n是否要创建它 (如果适用)?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
            content = self.loaded_world_name 
        else:
            try:
                with open(target_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取 '{file_description}' 失败: {str(e)}")
                return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"编辑世界文件: {file_description}")
        dialog.setMinimumSize(600, 400)
        layout = QVBoxLayout(dialog)
        editor = QTextEdit()
        editor.setPlainText(content)
        layout.addWidget(editor)
        buttons = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(lambda: self.save_generic_world_file(editor.toPlainText(), target_file_path, dialog, file_description))
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        dialog.exec()

    def save_generic_world_file(self, content, file_path, dialog, file_description="文件"):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            QMessageBox.information(self, "成功", f"'{file_description}' 已保存.")
            dialog.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存 '{file_description}' 失败: {str(e)}")


    def export_pack_config(self, pack_type):
        if not self.loaded_world_name:
            QMessageBox.warning(self, "警告", "请先加载一个世界.")
            return

        data = getattr(self, f"world_{pack_type}_packs_data")
        if not data: 
            QMessageBox.information(self, "信息", f"当前世界没有 {pack_type} 包配置可导出.")
            return

        default_filename = f"{self.loaded_world_name}_{pack_type}_packs_{datetime.now().strftime('%Y%m%d')}.json"
        file_path, _ = QFileDialog.getSaveFileName(self, f"导出 {pack_type} 包配置",
                                                 os.path.join(self.server_root_path or "", default_filename),
                                                 "JSON 文件 (*.json)")
        if not file_path:
            return

        export_data = {
            "manager_version": "8.3", 
            "export_time": datetime.now().isoformat(),
            "world_name": self.loaded_world_name,
            "pack_type": pack_type,
            "packs": data
        }
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            self.update_status(f"{pack_type.capitalize()} 包配置已导出到: {os.path.basename(file_path)}", "success")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出 {pack_type} 包配置失败: {str(e)}")


    def import_pack_config(self, pack_type):
        if not self.loaded_world_name:
            QMessageBox.warning(self, "警告", "请先加载一个世界.")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, f"导入 {pack_type} 包配置",
                                                 self.server_root_path or "", 
                                                 "JSON 文件 (*.json)")
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)

            if not isinstance(imported_data, dict) or "packs" not in imported_data or \
               not isinstance(imported_data["packs"], list):
                raise ValueError("无效的配置文件格式.缺少 'packs' 列表.")
            
            imported_pack_type = imported_data.get("pack_type")
            if imported_pack_type != pack_type:
                raise ValueError(f"配置文件类型不匹配.期望 '{pack_type}' 包配置, 得到 '{imported_pack_type}'.")

            num_packs = len(imported_data["packs"])
            reply = QMessageBox.question(self, "确认导入",
                                       f"确定要导入 {num_packs} 个 {pack_type} 包配置吗?\n这将覆盖当前加载世界的 {pack_type} 包配置.",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                setattr(self, f"world_{pack_type}_packs_data", imported_data["packs"])
                self.save_world_json_file(pack_type) 
                self.refresh_world_packs_tree(pack_type)
                self.update_status(f"{pack_type.capitalize()} 包配置已从 '{os.path.basename(file_path)}' 导入.", "success")

        except json.JSONDecodeError:
            QMessageBox.critical(self, "错误", "导入失败: 文件不是有效的JSON.")
        except ValueError as ve: 
             QMessageBox.critical(self, "错误", f"导入失败: {str(ve)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入 {pack_type} 包配置时发生未知错误: {str(e)}")

    def toggle_dark_mode(self):
        if self.dark_mode_btn.isChecked():
            QApplication.instance().setPalette(self.dark_palette)
            self.dark_mode_btn.setText("切换浅色模式")
            current_message = self.status_bar.currentMessage()
            if current_message: 
                self.update_status(current_message, "info") 
        else:
            QApplication.instance().setPalette(self.light_palette) 
            self.dark_mode_btn.setText("切换深色模式")
            current_message = self.status_bar.currentMessage()
            if current_message:
                self.update_status(current_message, "info")
        

    def update_server_controls_state(self):
        server_running = self.server_process is not None and \
                         self.server_process.state() != QProcess.ProcessState.NotRunning
        
        root_loaded = bool(self.server_root_path)

        self.start_server_btn.setEnabled(root_loaded and not server_running)
        self.stop_server_btn.setEnabled(root_loaded and server_running)
        self.server_command_input.setEnabled(root_loaded and server_running)
        self.send_command_btn.setEnabled(root_loaded and server_running)
        self.edit_server_properties_btn.setEnabled(root_loaded)

        if not root_loaded: 
            self.start_server_btn.setEnabled(False)
            self.stop_server_btn.setEnabled(False)
            self.server_command_input.setEnabled(False)
            self.send_command_btn.setEnabled(False)
            self.edit_server_properties_btn.setEnabled(False)


    def start_server(self):
        if not self.server_root_path:
            QMessageBox.warning(self, "错误", "请先加载服务器根目录.")
            return

        server_exe_path = os.path.join(self.server_root_path, self.server_executable_name)
        if not os.path.exists(server_exe_path):
            QMessageBox.critical(self, "错误", f"服务器可执行文件未找到: {server_exe_path}\n请确保 '{self.server_executable_name}' 在服务器根目录中.")
            return
        
        if self.server_process and self.server_process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.information(self, "提示", "服务器已在运行中.")
            return

        self.server_process = QProcess(self)
        self.server_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels) 
        self.server_process.readyReadStandardOutput.connect(self.handle_server_output)
        self.server_process.started.connect(self.handle_server_started)
        self.server_process.finished.connect(self.handle_server_finished) 
        self.server_process.errorOccurred.connect(self.handle_server_error)
        
        self.server_process.setWorkingDirectory(self.server_root_path)
        
        self.server_log_display.clear()
        self.server_log_display.append(f"正在启动服务器: {server_exe_path}...")
        
        if platform.system() == "Linux" and not os.access(server_exe_path, os.X_OK):
             self.server_log_display.append(f"警告: {self.server_executable_name} 可能没有执行权限.请尝试 'chmod +x {self.server_executable_name}'.")

        self.server_process.start(server_exe_path, [])

    def stop_server(self):
        if self.server_process and self.server_process.state() != QProcess.ProcessState.NotRunning:
            self.server_log_display.append("正在发送 'stop' 命令到服务器...")
            self.server_process.write("stop\n".encode('utf-8')) 
            self.server_process.waitForBytesWritten(1000)

            if not self.server_process.waitForFinished(5000): 
                self.server_log_display.append("服务器未能优雅停止,正在强制终止...")
                self.server_process.terminate() 
                if not self.server_process.waitForFinished(2000): 
                    self.server_log_display.append("服务器未能终止,正在强制杀死进程...")
                    self.server_process.kill() 
        else:
            self.server_log_display.append("服务器未运行或已停止.")
        self.update_server_controls_state()

    def send_server_command(self):
        if self.server_process and self.server_process.state() != QProcess.ProcessState.NotRunning:
            command = self.server_command_input.text().strip()
            if command:
                self.server_log_display.append(f"> {command}") 
                self.server_process.write((command + "\n").encode('utf-8'))
                self.server_process.waitForBytesWritten(500)
                self.server_command_input.clear()
        else:
            QMessageBox.warning(self, "错误", "服务器未运行.")

    def handle_server_output(self):
        if not self.server_process: return
        data = self.server_process.readAllStandardOutput().data().decode('utf-8', errors='replace')
        
        self.server_log_display.moveCursor(QTextCursor.MoveOperation.End)
        self.server_log_display.insertPlainText(data)

    def handle_server_started(self):
        self.server_log_display.append("服务器已启动.\n")
        self.update_status("服务器运行中", "success")
        self.update_server_controls_state()

    def handle_server_finished(self, exit_code, exit_status):
        status_msg = "已停止" if exit_status == QProcess.ExitStatus.NormalExit else "意外终止"
        self.server_log_display.append(f"\n服务器进程 {status_msg} (退出码: {exit_code}).")
        self.update_status(f"服务器 {status_msg}", "info")
        self.server_process = None 
        self.update_server_controls_state()

    def handle_server_error(self, error):
        error_map = {
            QProcess.ProcessError.FailedToStart: "启动失败", QProcess.ProcessError.Crashed: "崩溃",
            QProcess.ProcessError.Timedout: "超时", QProcess.ProcessError.ReadError: "读取错误",
            QProcess.ProcessError.WriteError: "写入错误", QProcess.ProcessError.UnknownError: "未知错误"
        }
        error_string = error_map.get(error, "未知错误")
        self.server_log_display.append(f"服务器进程错误: {error_string}")
        self.update_status(f"服务器错误: {error_string}", "error")
        self.server_process = None 
        self.update_server_controls_state()
        
    def edit_server_properties(self):
        if not self.server_root_path:
            QMessageBox.warning(self, "警告", "请先加载服务器根目录.")
            return

        properties_path = os.path.join(self.server_root_path, "server.properties")
        
        content = ""
        if os.path.exists(properties_path):
            try:
                with open(properties_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取 server.properties 失败: {str(e)}")
                return
        else:
            QMessageBox.information(self, "提示", f"server.properties 文件未找到于: {properties_path}\n如果保存,将会创建一个新文件.")
            content = (
                "# Minecraft Bedrock Server Properties\n"
                f"# {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                "server-name=Bedrock Dedicated Server\n"
                "gamemode=survival\n"
                "difficulty=easy\n"
                "allow-cheats=false\n"
            )


        dialog = QDialog(self)
        dialog.setWindowTitle("编辑 server.properties")
        dialog.setMinimumSize(700, 500)
        layout = QVBoxLayout(dialog)
        editor = QTextEdit()
        editor.setFont(QFont("Consolas", 10))
        editor.setPlainText(content)
        layout.addWidget(editor)
        
        buttons = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        save_btn.clicked.connect(lambda: self.save_server_properties(editor.toPlainText(), properties_path, dialog))
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton))
        cancel_btn.clicked.connect(dialog.reject)
        
        buttons.addStretch()
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
        
        dialog.exec()

    def save_server_properties(self, content, properties_path, dialog):
        try:
            with open(properties_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.update_status("server.properties 已保存.", "success")
            QMessageBox.information(self, "成功", "server.properties 已保存.\n某些更改可能需要重启服务器才能生效.")
            dialog.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存 server.properties 失败: {str(e)}")
            
    def open_server_folder(self, folder_name):
        if not self.server_root_path:
            QMessageBox.warning(self, "警告", "请先加载服务器根目录.")
            return
        
        path_to_open = os.path.join(self.server_root_path, folder_name)
        
        if not os.path.exists(path_to_open):
            if folder_name in ["behavior_packs", "resource_packs", "worlds", "world_backups"]:
                 reply = QMessageBox.question(self, "文件夹不存在",
                                           f"文件夹 '{folder_name}' 不存在.\n是否要创建它?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                 if reply == QMessageBox.StandardButton.Yes:
                     try:
                         os.makedirs(path_to_open, exist_ok=True)
                         self.update_status(f"文件夹 '{folder_name}' 已创建.", "info")
                     except Exception as e:
                         QMessageBox.critical(self, "错误", f"创建文件夹 '{folder_name}' 失败: {e}")
                         return 
                 else:
                    return 
            else: 
                QMessageBox.information(self, "提示", f"文件夹 '{folder_name}' 不存在于: {path_to_open}")
                return

        if QDesktopServices.openUrl(QUrl.fromLocalFile(path_to_open)):
            self.update_status(f"已打开文件夹: {folder_name}", "info")
        else:
            QMessageBox.warning(self, "错误", f"无法打开文件夹: {path_to_open}")

    def closeEvent(self, event):
        if self.server_process and self.server_process.state() != QProcess.ProcessState.NotRunning:
            reply = QMessageBox.question(self, "服务器运行中",
                                       "服务器仍在运行中.是否要停止服务器并退出?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                                       QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_server()
                event.accept()
            elif reply == QMessageBox.StandardButton.No: 
                event.accept()
            else: 
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PackManagerApp()
    window.show()
    sys.exit(app.exec())
