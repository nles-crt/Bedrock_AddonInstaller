import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import uuid
import os
import shutil
import zipfile
import tempfile

class PackManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Bedrock Pack Manager v5 (Import Target)")
        self.root.geometry("850x630") # 稍微增加高度以容纳复选框

        # --- Data Storage ---
        self.behavior_packs_data = []
        self.resource_packs_data = []
        self.world_dir_path = ""
        self.server_root_path = ""
        self.behavior_json_path = ""
        self.resource_json_path = ""

        # --- Styling ---
        style = ttk.Style()
        style.theme_use('clam')
        # ... (样式与之前相同)
        style.configure("TButton", padding=6, relief="flat", font=('Calibri', 10))
        style.configure("Treeview.Heading", font=('Calibri', 10, 'bold'))
        style.configure("TLabel", padding=3, font=('Calibri', 10))
        style.configure("TEntry", padding=3, font=('Calibri', 10))
        style.configure("TLabelframe.Label", font=('Calibri', 11, 'bold'))
        style.configure("Warning.TLabel", foreground="orange", font=('Calibri', 10, 'italic'))
        style.configure("TCheckbutton", font=('Calibri', 10))


        # --- Top Controls ---
        top_controls_frame = ttk.Frame(root)
        top_controls_frame.pack(pady=10, padx=10, fill=tk.X)

        load_world_button = ttk.Button(top_controls_frame, text="加载世界目录",
                                      command=self.select_world_directory)
        load_world_button.pack(side=tk.LEFT, padx=5)

        self.world_dir_label = ttk.Label(top_controls_frame, text="未加载世界目录")
        self.world_dir_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # --- Mcaddon Import Controls Frame ---
        mcaddon_frame = ttk.Frame(root)
        mcaddon_frame.pack(pady=(0,5), padx=10, fill=tk.X)

        self.mcaddon_import_button = ttk.Button(mcaddon_frame, text="导入 .mcaddon",
                                               command=self.import_mcaddon, state=tk.DISABLED)
        self.mcaddon_import_button.pack(side=tk.LEFT, padx=(0,10))

        self.import_to_world_var = tk.BooleanVar(value=False) # Default to server packs
        self.import_to_world_check = ttk.Checkbutton(mcaddon_frame,
                                                    text="导入到当前世界文件夹 (如果不存在则创建)",
                                                    variable=self.import_to_world_var,
                                                    state=tk.DISABLED)
        self.import_to_world_check.pack(side=tk.LEFT)


        # --- Main Paned Window for resizable sections ---
        packs_paned_window = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        packs_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)


        # --- Behavior Packs Section ---
        behavior_frame = ttk.LabelFrame(packs_paned_window, text="行为包 (world_behavior_packs.json)")
        packs_paned_window.add(behavior_frame, weight=1)
        self.create_pack_section(behavior_frame, "behavior")

        # --- Resource Packs Section ---
        resource_frame = ttk.LabelFrame(packs_paned_window, text="资源包 (world_resource_packs.json)")
        packs_paned_window.add(resource_frame, weight=1)
        self.create_pack_section(resource_frame, "resource")


        # --- Status Bar ---
        self.status_bar = ttk.Label(root, text="准备就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5,0), padx=10)

    # create_pack_section, _validate_pack_input, _load_json_data_from_file,
    # populate_pack_listbox, add_pack_entry_to_json, remove_pack_entry_from_json, save_json_file
    # ... (这些方法与 v4 版本基本相同，此处省略以减少篇幅)
    def create_pack_section(self, parent_frame, pack_type):
        file_controls_frame = ttk.Frame(parent_frame)
        file_controls_frame.pack(pady=5, padx=5, fill=tk.X)

        save_button = ttk.Button(file_controls_frame, text="保存更改到JSON",
                                command=lambda pt=pack_type: self.save_json_file(pt))
        save_button.pack(side=tk.LEFT, padx=5)
        setattr(self, f"{pack_type}_save_button", save_button)
        save_button.config(state=tk.DISABLED)

        file_status_label = ttk.Label(file_controls_frame, text="JSON未加载")
        file_status_label.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        setattr(self, f"{pack_type}_file_status_label", file_status_label)

        list_frame = ttk.Frame(parent_frame)
        list_frame.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)

        cols = ("Pack ID", "Version") # Simplified columns
        pack_listbox = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        pack_listbox.heading("Pack ID", text="Pack ID")
        pack_listbox.heading("Version", text="版本")
        pack_listbox.column("Pack ID", width=220, stretch=tk.YES)
        pack_listbox.column("Version", width=100, stretch=tk.YES, anchor=tk.CENTER)
        setattr(self, f"{pack_type}_listbox", pack_listbox)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=pack_listbox.yview)
        pack_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        pack_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        add_remove_frame = ttk.Frame(parent_frame)
        add_remove_frame.pack(pady=5, padx=5, fill=tk.X)

        ttk.Label(add_remove_frame, text="Pack ID (UUID):").grid(row=0, column=0, padx=2, pady=2, sticky="w")
        pack_id_entry = ttk.Entry(add_remove_frame, width=30)
        pack_id_entry.grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        setattr(self, f"{pack_type}_id_entry", pack_id_entry)

        ttk.Label(add_remove_frame, text="版本 (例如: 1,0,0):").grid(row=1, column=0, padx=2, pady=2, sticky="w")
        version_entry = ttk.Entry(add_remove_frame, width=15)
        version_entry.grid(row=1, column=1, padx=2, pady=2, sticky="w")
        setattr(self, f"{pack_type}_version_entry", version_entry)

        add_button = ttk.Button(add_remove_frame, text="添加包到JSON",
                               command=lambda pt=pack_type: self.add_pack_entry_to_json(pt))
        add_button.grid(row=0, column=2, rowspan=2, padx=5, pady=2, sticky="ns")

        remove_button = ttk.Button(add_remove_frame, text="从JSON移除",
                                  command=lambda pt=pack_type: self.remove_pack_entry_from_json(pt))
        remove_button.grid(row=0, column=3, rowspan=2, padx=5, pady=2, sticky="ns")
        add_remove_frame.columnconfigure(1, weight=1)

        setattr(self, f"{pack_type}_add_button", add_button)
        setattr(self, f"{pack_type}_remove_button", remove_button)
        add_button.config(state=tk.DISABLED)
        remove_button.config(state=tk.DISABLED)

    def update_status(self, message, level="info"):
        color = "black"
        if level == "warning":
            color = "darkorange"
        elif level == "error":
            color = "red"
        self.status_bar.config(text=message, foreground=color)
        self.root.update_idletasks()

    def select_world_directory(self):
        dir_path = filedialog.askdirectory(title="选择 Minecraft 世界目录")
        if not dir_path:
            return

        self.world_dir_path = dir_path
        self.world_dir_label.config(text=f"当前世界: {os.path.basename(dir_path)}")
        self.update_status(f"已选择世界目录: {dir_path}")

        potential_server_root = os.path.dirname(self.world_dir_path)
        if os.path.basename(potential_server_root).lower() == "worlds":
             potential_server_root = os.path.dirname(potential_server_root)
        self.server_root_path = potential_server_root
        self.update_status(f"推断的服务器根目录: {self.server_root_path}")

        server_bp_path = os.path.join(self.server_root_path, "behavior_packs")
        server_rp_path = os.path.join(self.server_root_path, "resource_packs")

        can_import_mcaddon = False
        if os.path.isdir(server_bp_path) and os.path.isdir(server_rp_path):
            can_import_mcaddon = True
            self.update_status(f"服务器级包目录找到。")
        else:
            # Server level packs dir not mandatory for import if user chooses world import
            self.update_status(f"提示: 未在 {self.server_root_path} 找到服务器级 behavior_packs/resource_packs 文件夹。", level="info")


        if self.world_dir_path: # If a world is loaded, mcaddon import is possible (either to server or world)
            self.mcaddon_import_button.config(state=tk.NORMAL)
            self.import_to_world_check.config(state=tk.NORMAL)
        else:
            self.mcaddon_import_button.config(state=tk.DISABLED)
            self.import_to_world_check.config(state=tk.DISABLED)


        # ... (rest of the JSON loading logic is the same as v4)
        self.behavior_json_path = os.path.join(self.world_dir_path, "world_behavior_packs.json")
        self.resource_json_path = os.path.join(self.world_dir_path, "world_resource_packs.json")

        if os.path.exists(self.behavior_json_path):
            self.behavior_packs_data = self._load_json_data_from_file(self.behavior_json_path)
            self.behavior_file_status_label.config(text="world_behavior_packs.json 已加载", style="TLabel")
            self.behavior_save_button.config(state=tk.NORMAL)
        else:
            self.behavior_packs_data = []
            self.behavior_file_status_label.config(text="world_behavior_packs.json 未找到 (可创建)", style="Warning.TLabel")
            self.update_status(f"警告: {self.behavior_json_path} 未找到。可手动添加包并保存以创建。", level="warning")
            self.behavior_save_button.config(state=tk.DISABLED)

        self.populate_pack_listbox("behavior")
        self.behavior_add_button.config(state=tk.NORMAL)
        self.behavior_remove_button.config(state=tk.NORMAL if self.behavior_packs_data else tk.DISABLED)

        if os.path.exists(self.resource_json_path):
            self.resource_packs_data = self._load_json_data_from_file(self.resource_json_path)
            self.resource_file_status_label.config(text="world_resource_packs.json 已加载", style="TLabel")
            self.resource_save_button.config(state=tk.NORMAL)
        else:
            self.resource_packs_data = []
            self.resource_file_status_label.config(text="world_resource_packs.json 未找到 (可创建)", style="Warning.TLabel")
            self.update_status(f"警告: {self.resource_json_path} 未找到。可手动添加包并保存以创建。", level="warning")
            self.resource_save_button.config(state=tk.DISABLED)

        self.populate_pack_listbox("resource")
        self.resource_add_button.config(state=tk.NORMAL)
        self.resource_remove_button.config(state=tk.NORMAL if self.resource_packs_data else tk.DISABLED)

    def _load_json_data_from_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON文件顶层结构必须是一个列表")
            for item in data:
                if not (isinstance(item, dict) and "pack_id" in item and "version" in item):
                    raise ValueError("列表中的每个项目必须包含 'pack_id' 和 'version'")
                if not isinstance(item["version"], list) or len(item["version"]) != 3:
                     raise ValueError(f"Pack ID {item['pack_id']} 的 'version' 必须是包含三个数字的列表")
            self.update_status(f"{os.path.basename(filepath)} 加载成功。")
            return data
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            messagebox.showerror("JSON错误", f"加载 {os.path.basename(filepath)} 失败: 无效的 JSON 文件格式！")
            self.update_status(f"错误: {os.path.basename(filepath)} JSON格式无效。", level="error")
        except ValueError as ve:
            messagebox.showerror("JSON错误", f"加载 {os.path.basename(filepath)} 失败: JSON 文件内容格式不正确: {ve}")
            self.update_status(f"错误: {os.path.basename(filepath)} 内容格式不正确。", level="error")
        except Exception as e:
            messagebox.showerror("加载错误", f"加载 {os.path.basename(filepath)} 时发生未知错误: {e}")
            self.update_status(f"错误: 加载 {os.path.basename(filepath)} 时发生未知错误。", level="error")
        return []

    def populate_pack_listbox(self, pack_type_str):
        listbox = getattr(self, f"{pack_type_str}_listbox")
        json_data = getattr(self, f"{pack_type_str}_packs_data")

        for item in listbox.get_children():
            listbox.delete(item)

        for pack in json_data:
            pack_id = pack.get("pack_id", "N/A")
            version_arr = pack.get("version", ["N/A"]*3)
            version_str = f"[{', '.join(map(str, version_arr))}]"
            listbox.insert("", tk.END, values=(pack_id, version_str))

    def _validate_pack_input(self, pack_id_str, version_str):
        if not pack_id_str or not version_str:
            messagebox.showwarning("输入错误", "Pack ID 和版本不能为空。")
            return None, None
        try:
            uuid.UUID(pack_id_str)
        except ValueError:
            messagebox.showwarning("输入错误", "Pack ID 不是有效的 UUID 格式。")
            return None, None
        try:
            version_parts_str = version_str.replace('[','').replace(']','').replace(' ','')
            version_parts = [int(v.strip()) for v in version_parts_str.split(',')]
            if len(version_parts) != 3:
                raise ValueError("版本号必须包含三个数字。")
            return pack_id_str, version_parts
        except ValueError as e:
            messagebox.showwarning("输入错误", f"版本格式错误: {e}\n请输入类似 '1,0,0' 或 '[1,0,0]' 的格式。")
            return None, None

    def add_pack_entry_to_json(self, pack_type_str):
        if not self.world_dir_path:
            messagebox.showerror("错误", "请先加载一个世界目录。")
            return

        id_entry = getattr(self, f"{pack_type_str}_id_entry")
        version_entry = getattr(self, f"{pack_type_str}_version_entry")
        data_list = getattr(self, f"{pack_type_str}_packs_data")

        pack_id_str_raw = id_entry.get().strip()
        version_str_raw = version_entry.get().strip()
        pack_id_str, version_arr = self._validate_pack_input(pack_id_str_raw, version_str_raw)

        if not pack_id_str or not version_arr:
            return

        for pack in data_list:
            if pack.get("pack_id") == pack_id_str:
                if pack.get("version") != version_arr:
                     if messagebox.askyesno("版本更新?", f"Pack ID '{pack_id_str}' 已存在于 {pack_type_str} JSON列表中，但版本不同。\n现有: {pack.get('version')}, 新: {version_arr}\n是否更新版本?"):
                        pack["version"] = version_arr
                        self.update_status(f"已更新 {pack_type_str} pack: {pack_id_str} 的版本。请记得保存。")
                        self.populate_pack_listbox(pack_type_str)
                        return
                else:
                    messagebox.showwarning("重复添加", f"Pack ID '{pack_id_str}' (版本相同) 已存在于 {pack_type_str} JSON列表中。")
                return

        new_pack = {"pack_id": pack_id_str, "version": version_arr}
        data_list.append(new_pack)
        self.populate_pack_listbox(pack_type_str)
        id_entry.delete(0, tk.END)
        version_entry.delete(0, tk.END)
        self.update_status(f"已添加 {pack_type_str} pack: {pack_id_str} 到JSON列表。请记得保存。")
        getattr(self, f"{pack_type_str}_save_button").config(state=tk.NORMAL)
        getattr(self, f"{pack_type_str}_remove_button").config(state=tk.NORMAL)


    def remove_pack_entry_from_json(self, pack_type_str):
        if not self.world_dir_path:
            messagebox.showerror("错误", "请先加载一个世界目录。")
            return

        listbox = getattr(self, f"{pack_type_str}_listbox")
        data_list = getattr(self, f"{pack_type_str}_packs_data")
        selected_item_id = listbox.selection()

        if not selected_item_id:
            messagebox.showwarning("选择错误", "请先选择一个要移除的包。")
            return

        selected_item = listbox.item(selected_item_id)
        pack_id_to_remove = selected_item['values'][0]

        original_length = len(data_list)
        new_data_list = [pack for pack in data_list if pack.get("pack_id") != pack_id_to_remove]

        if len(new_data_list) < original_length:
            if pack_type_str == "behavior":
                self.behavior_packs_data = new_data_list
            else:
                self.resource_packs_data = new_data_list
            self.populate_pack_listbox(pack_type_str)
            self.update_status(f"已从JSON列表移除 {pack_type_str} pack: {pack_id_to_remove}。请记得保存。")
            if not new_data_list:
                getattr(self, f"{pack_type_str}_remove_button").config(state=tk.DISABLED)
        else:
            messagebox.showerror("错误", "无法在JSON数据中找到要移除的包 (ID: " + pack_id_to_remove + ")。")
            self.update_status(f"错误: 从JSON列表移除 {pack_type_str} pack 失败: {pack_id_to_remove}", level="error")

    def save_json_file(self, pack_type_str):
        if not self.world_dir_path:
            messagebox.showerror("错误", "未加载世界目录，无法保存。")
            return

        if pack_type_str == "behavior":
            filepath = self.behavior_json_path
            data = self.behavior_packs_data
        else: # resource
            filepath = self.resource_json_path
            data = self.resource_packs_data

        if not filepath:
            messagebox.showerror("错误", "文件路径未知，无法保存。")
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("成功", f"{os.path.basename(filepath)} 文件已成功保存到:\n{filepath}")
            self.update_status(f"{os.path.basename(filepath)} 保存成功。")
            getattr(self, f"{pack_type_str}_file_status_label").config(text=f"{os.path.basename(filepath)} 已加载", style="TLabel")
        except Exception as e:
            messagebox.showerror("保存错误", f"保存文件时发生错误: {e}")
            self.update_status(f"错误: 保存 {os.path.basename(filepath)} 失败。", level="error")

    def import_mcaddon(self):
        if not self.world_dir_path: # World must be loaded to define context for JSON updates
            messagebox.showerror("错误", "请先加载一个世界目录。")
            return
        if not self.server_root_path and not self.import_to_world_var.get():
             messagebox.showerror("错误", "无法推断服务器根目录，且未选择导入到世界文件夹。请检查服务器结构或选择导入到世界。")
             return


        mcaddon_path = filedialog.askopenfilename(
            title="选择 .mcaddon 文件导入",
            filetypes=((".mcaddon files", "*.mcaddon"), ("All files", "*.*"))
        )
        if not mcaddon_path:
            return

        self.update_status(f"正在导入 {os.path.basename(mcaddon_path)}...")
        packs_added_to_json_count = {"behavior": 0, "resource": 0}
        packs_copied_count = {"behavior": 0, "resource": 0}
        import_target_desc = ""


        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(mcaddon_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                for item_name in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item_name)
                    if os.path.isdir(item_path):
                        manifest_path = os.path.join(item_path, "manifest.json")
                        if os.path.exists(manifest_path):
                            try:
                                with open(manifest_path, 'r', encoding='utf-8') as mf:
                                    manifest_data = json.load(mf)

                                pack_id = manifest_data.get("header", {}).get("uuid")
                                version_arr = manifest_data.get("header", {}).get("version")
                                pack_name = manifest_data.get("header", {}).get("name", item_name)

                                if not pack_id or not version_arr or len(version_arr) != 3:
                                    self.update_status(f"警告: {item_name} manifest.json 缺少 UUID/版本，已跳过。", level="warning")
                                    continue

                                pack_type_module = manifest_data.get("modules", [{}])[0].get("type")
                                base_target_dir = ""
                                data_list_to_update = None
                                pack_type_str_for_json = None # 'behavior' or 'resource' for JSON list

                                if self.import_to_world_var.get():
                                    import_target_desc = "当前世界"
                                    base_target_dir = self.world_dir_path
                                else: # Import to server
                                    import_target_desc = "服务器"
                                    if not self.server_root_path: # Should have been checked earlier but double check
                                        messagebox.showerror("错误", "无法确定服务器根目录用于导入。")
                                        return
                                    base_target_dir = self.server_root_path

                                target_pack_subdir_name = "" # e.g., "behavior_packs" or "resource_packs"

                                if pack_type_module == "data": # Behavior pack
                                    target_pack_subdir_name = "behavior_packs"
                                    data_list_to_update = self.behavior_packs_data
                                    pack_type_str_for_json = "behavior"
                                elif pack_type_module == "resources": # Resource pack
                                    target_pack_subdir_name = "resource_packs"
                                    data_list_to_update = self.resource_packs_data
                                    pack_type_str_for_json = "resource"
                                else:
                                    self.update_status(f"警告: {pack_name} ({item_name}) 类型未知 ({pack_type_module})，已跳过。", level="warning")
                                    continue

                                # Determine final installation directory and create if needed
                                final_install_packs_dir = os.path.join(base_target_dir, target_pack_subdir_name)
                                os.makedirs(final_install_packs_dir, exist_ok=True)
                                target_install_path = os.path.join(final_install_packs_dir, item_name)


                                # Copy pack folder
                                if os.path.exists(target_install_path):
                                    if messagebox.askyesno("覆盖确认",
                                                           f"包 '{pack_name}' ({item_name}) 已存在于 {import_target_desc} 目录:\n{target_install_path}\n是否覆盖?"):
                                        shutil.rmtree(target_install_path)
                                        shutil.copytree(item_path, target_install_path)
                                        self.update_status(f"已覆盖 '{pack_name}' 到 {import_target_desc} {pack_type_str_for_json}_packs 目录。")
                                        packs_copied_count[pack_type_str_for_json] += 1
                                    else:
                                        self.update_status(f"已跳过复制已存在的包 '{pack_name}'。")
                                else:
                                    shutil.copytree(item_path, target_install_path)
                                    self.update_status(f"已复制 '{pack_name}' 到 {import_target_desc} {pack_type_str_for_json}_packs 目录。")
                                    packs_copied_count[pack_type_str_for_json] += 1

                                # Add/Update entry in the world's JSON data (in memory)
                                existing_pack_in_json = next((p for p in data_list_to_update if p.get("pack_id") == pack_id), None)
                                if not existing_pack_in_json:
                                    data_list_to_update.append({"pack_id": pack_id, "version": version_arr})
                                    packs_added_to_json_count[pack_type_str_for_json] += 1
                                    getattr(self, f"{pack_type_str_for_json}_save_button").config(state=tk.NORMAL)
                                    getattr(self, f"{pack_type_str_for_json}_remove_button").config(state=tk.NORMAL)
                                elif existing_pack_in_json.get("version") != version_arr:
                                    if messagebox.askyesno("JSON版本更新确认",
                                                           f"包 '{pack_name}' (ID: {pack_id}) 已在当前世界 {pack_type_str_for_json}.json 列表中，但版本不同。\n"
                                                           f"JSON中版本: {existing_pack_in_json.get('version')}, .mcaddon中版本: {version_arr}\n"
                                                           f"是否更新此世界JSON中的版本号?"):
                                        existing_pack_in_json["version"] = version_arr
                                        self.update_status(f"世界JSON中包 '{pack_name}' 的版本已更新。")
                                self.populate_pack_listbox(pack_type_str_for_json)

                            except json.JSONDecodeError:
                                self.update_status(f"错误: {item_name} manifest.json 格式无效，已跳过。", level="error")
                            except Exception as e_manifest:
                                self.update_status(f"错误: 处理 {item_name} manifest.json 时出错: {e_manifest}", level="error")
            # ... (导入总结消息与之前相同，但用 import_target_desc)
            summary_messages = []
            if packs_copied_count["behavior"] > 0: summary_messages.append(f"复制了 {packs_copied_count['behavior']} 个行为包到{import_target_desc}目录")
            if packs_copied_count["resource"] > 0: summary_messages.append(f"复制了 {packs_copied_count['resource']} 个资源包到{import_target_desc}目录")
            if packs_added_to_json_count["behavior"] > 0: summary_messages.append(f"添加/更新了 {packs_added_to_json_count['behavior']} 个行为包条目到当前世界JSON列表")
            if packs_added_to_json_count["resource"] > 0: summary_messages.append(f"添加/更新了 {packs_added_to_json_count['resource']} 个资源包条目到当前世界JSON列表")

            final_msg = f".mcaddon 导入完成: {'; '.join(summary_messages) if summary_messages else '未找到或处理任何有效的包。'}"
            final_msg += "\n请检查列表并点击 '保存更改到JSON' 以将更改应用到当前世界的JSON文件。"
            messagebox.showinfo("导入结果", final_msg)
            self.update_status(final_msg)

        except zipfile.BadZipFile:
            messagebox.showerror("导入错误", f"{os.path.basename(mcaddon_path)} 不是一个有效的 .mcaddon (ZIP) 文件。")
            self.update_status(f"错误: {os.path.basename(mcaddon_path)} 不是有效的ZIP文件。", level="error")
        except Exception as e:
            messagebox.showerror("导入错误", f"导入 .mcaddon 时发生未知错误: {e}")
            self.update_status(f"错误: 导入 .mcaddon 时发生未知错误: {e}", level="error")


if __name__ == "__main__":
    root = tk.Tk()
    app = PackManagerApp(root)
    root.mainloop()