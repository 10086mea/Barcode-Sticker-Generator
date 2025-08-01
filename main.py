import tkinter as tk
from tkinter import font, filedialog, messagebox, ttk, colorchooser
import json
from PIL import Image, ImageDraw, ImageFont, ImageTk
import barcode
from barcode.writer import ImageWriter
import io
import os
import sys
import math

# --- 全局配置 (默认值) ---
DEFAULT_CANVAS_WIDTH = 800
DEFAULT_CANVAS_HEIGHT = 400
BACKGROUND_COLOR = "#FFFFFF"
HIGHLIGHT_COLOR = "#DDEEFF" # 用于高亮选定元素行的颜色
SELECTION_BORDER_COLOR = "#CC0000" # 用于拖拽时高亮选框的颜色

class StickerGenerator:
    """
    一个功能强大的条形码贴纸生成器GUI应用。
    V4.1 版本更新:
    - 新功能: 实现自由变换功能。当单个元素被选中时，会出现带控制柄的边框。
    - 新功能: 用户可以通过拖动控制柄来直观地调整元素的大小（对文本是字号，对条码是宽高）。
    - 新功能: 鼠标在画布上移动时，会根据位置（元素、控制柄、背景）显示不同的光标。
    - 优化: 交互逻辑重构，以支持新的变换模式。
    - 保留了V4.0版本的所有功能。
    """
    def __init__(self, root):
        self.root = root
        self.root.title("高级条形码贴纸生成器 V4.1 (自由变换)")
        self.root.geometry("1350x800") # 稍微加宽窗口以适应更宽的控件

        # --- 状态变量 ---
        self._drag_data = {"x": 0, "y": 0, "items": {}}
        self.selection = set()
        self.preview_tk_img = None
        self.ctrl_pressed = False
        self.preview_scale = 1.0
        self.preview_offset_x = 0
        self.preview_offset_y = 0
        self.custom_text_counter = 0

        # --- 新增：自由变换相关状态 ---
        self.transform_mode = None  # 当前变换模式: 'move', 'tl', 'br', 等
        self.active_handle = None   # 当前被激活的控制柄
        self.transform_handles = {} # 存储控制柄的位置和类型
        self.handle_size = 8        # 控制柄在画布上的显示大小

        # --- 字体管理 ---
        self.font_map = {}
        self.available_jp_fonts = []
        self.available_impact_fonts = []
        self._find_system_fonts()
        
        if not self.available_jp_fonts:
            messagebox.showwarning("字体警告", "未找到推荐的日文字体。")
            self.available_jp_fonts = ['sans-serif']
        if not self.available_impact_fonts:
            messagebox.showwarning("字体警告", "未找到Impact或类似字体。")
            self.available_impact_fonts = ['sans-serif']

        self.init_data()
        self._create_styles()
        self._create_widgets()
        
        self.root.after(100, self.update_preview)

    def init_data(self):
        """初始化或重置所有数据"""
        self.data = {
            "info": {
                "cat1": "趣味系書籍", "code": "G1068036", "barcode_data": "G1068036", "cat2": "原画集マンガアニメ系",
                "title": "ソードアート・オンライン abec画集 Wanderers", "list_price": "3080",
                "used_price_base": "2273", "sale_date": "20.03.27", "tax_date": "24.06.06"
            },
            "config": {
                "jp_font": "Meiryo", "impact_font": "Impact", "tax_rate": 10.0,
                "strikethrough": True, "price_area_color": "#ffffff",
                "export_width": DEFAULT_CANVAS_WIDTH, "export_height": DEFAULT_CANVAS_HEIGHT, "show_border": True
            },
            "elements": {
                "barcode": {"pos": (408, 47), "size": (300, 70), "font_size": 0, "tag": "barcode", "vertical": False},
                "cat1": {"pos": (101, 131), "size": (0, 0), "font_size": 24, "tag": "cat1", "anchor": "s", "vertical": False, "line_spacing": 1.1},
                "code": {"pos": (302, 83), "size": (0, 0), "font_size": 24, "tag": "code", "anchor": "n", "vertical": False},
                "cat2": {"pos": (623, 133), "size": (0, 0), "font_size": 24, "tag": "cat2", "anchor": "s", "vertical": False, "line_spacing": 1.1},
                "title": {"pos": (32, 173), "size": (0, 0), "font_size": 25, "tag": "title", "anchor": "w", "vertical": False},
                "list_price": {"pos": (31, 222), "size": (0, 0), "font_size": 24, "tag": "list_price", "anchor": "w", "vertical": False},
                "used_label": {"pos": (117, 282), "size": (0, 0), "font_size": 70, "tag": "used_label", "anchor": "center", "vertical": False},
                "tax_date_label": {"pos": (72, 318), "size": (0, 0), "font_size": 32, "tag": "tax_date_label", "anchor": "n", "vertical": False, "line_spacing": 1.0},
                "tax_date_value": {"pos": (32, 394), "size": (0, 0), "font_size": 24, "tag": "tax_date_value", "anchor": "w", "vertical": False},
                "release_date": {"pos": (776, 217), "size": (0, 0), "font_size": 24, "tag": "release_date", "anchor": "e", "vertical": False},
                "price_breakdown": {"pos": (775, 259), "size": (0, 0), "font_size": 24, "tag": "price_breakdown", "anchor": "e", "vertical": False},
                "final_price": {"pos": (600, 348), "size": (0, 0), "font_size": 100, "tag": "final_price", "anchor": "center", "vertical": False}
            }
        }
        self.vars = {key: tk.StringVar(value=str(val)) for key, val in self.data['info'].items()}
        self.config_vars = {
            "jp_font": tk.StringVar(value=self.data['config']['jp_font']),
            "impact_font": tk.StringVar(value=self.data['config']['impact_font']),
            "tax_rate": tk.DoubleVar(value=self.data['config']['tax_rate']),
            "strikethrough": tk.BooleanVar(value=self.data['config']['strikethrough']),
            "price_area_color": tk.StringVar(value=self.data['config']['price_area_color']),
            "export_width": tk.StringVar(value=str(self.data['config']['export_width'])),
            "export_height": tk.StringVar(value=str(self.data['config']['export_height'])),
            "show_border": tk.BooleanVar(value=self.data['config']['show_border'])
        }
        self.element_vars = { key: {
                'x': tk.StringVar(value=str(val['pos'][0])),
                'y': tk.StringVar(value=str(val['pos'][1])),
                'w': tk.StringVar(value=str(val['size'][0])),
                'h': tk.StringVar(value=str(val['size'][1])),
                'font_size': tk.StringVar(value=str(val['font_size'])),
                'line_spacing': tk.StringVar(value=str(val.get('line_spacing', 1.0))),
                'vertical': tk.StringVar(value="竖排" if val.get('vertical') else "横排")
            } for key, val in self.data['elements'].items()
        }
        self.vars['used_price_base'].trace_add("write", lambda *args: self.update_preview())

    def _find_system_fonts(self):
        font_dirs = []
        if sys.platform == "win32":
            font_dirs.append(os.path.join(os.environ.get("SystemRoot", "C:/Windows"), "Fonts"))
        elif sys.platform == "darwin":
            font_dirs.extend(["/System/Library/Fonts", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")])
        else: # Linux
            font_dirs.extend(["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")])
        jp_fonts_map = {"Meiryo": ["meiryo.ttc", "meiryob.ttc"], "MS Gothic": ["msgothic.ttc"], "Yu Gothic": ["yugothib.ttf"]}
        impact_fonts_map = {"Impact": ["impact.ttf"], "Arial Black": ["ariblk.ttf"]}
        def search_fonts(font_dict):
            found_names = []
            for name, filenames in font_dict.items():
                if name in self.font_map: continue
                for d in font_dirs:
                    for filename in filenames:
                        font_path = os.path.join(d, filename)
                        if os.path.exists(font_path):
                            self.font_map[name] = font_path
                            found_names.append(name)
                            break
                    if name in self.font_map: break
            return found_names
        self.available_jp_fonts = search_fonts(jp_fonts_map)
        self.available_impact_fonts = search_fonts(impact_fonts_map)

    def _create_styles(self):
        s = ttk.Style()
        s.configure('TLabel', font=('Helvetica', 11))
        s.configure('TButton', font=('Helvetica', 11, 'bold'))
        s.configure('TEntry', font=('Helvetica', 11))
        s.configure('TLabelframe.Label', font=('Helvetica', 12, 'bold'))
        s.configure('Highlight.TLabel', font=('Helvetica', 10, 'bold'), background=HIGHLIGHT_COLOR)
        s.configure('Normal.TLabel', font=('Helvetica', 10, 'bold'))

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        controls_frame = ttk.Frame(paned_window, width=600)
        paned_window.add(controls_frame, weight=1)
        preview_frame = ttk.Frame(paned_window)
        paned_window.add(preview_frame, weight=2)
        update_button = ttk.Button(controls_frame, text="刷新预览", command=self.update_preview)
        update_button.pack(side=tk.BOTTOM, fill=tk.X, pady=5, ipady=5)
        file_frame = ttk.LabelFrame(controls_frame, text="文件操作", padding=10)
        file_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        ttk.Button(file_frame, text="载入模板", command=self.load_template).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(file_frame, text="保存模板", command=self.save_template).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(file_frame, text="导出图片", command=self.export_as_image).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        info_frame = ttk.LabelFrame(controls_frame, text="主要信息", padding=10)
        info_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        info_fields = [("分类1:", "cat1"), ("商品ID:", "code"), ("条码内容:", "barcode_data"), ("分类2:", "cat2"), ("作品名:", "title"), ("定价(円):", "list_price"), ("本体售价(円):", "used_price_base"), ("发售日:", "sale_date"), ("打印日期:", "tax_date")]
        for i, (label, key) in enumerate(info_fields):
            ttk.Label(info_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=1)
            ttk.Entry(info_frame, textvariable=self.vars[key], width=30).grid(row=i, column=1, sticky=tk.EW, pady=1)
        info_frame.grid_columnconfigure(1, weight=1)
        config_frame = ttk.LabelFrame(controls_frame, text="配置", padding=10)
        config_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        ttk.Label(config_frame, text="日文字体:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(config_frame, textvariable=self.config_vars['jp_font'], values=self.available_jp_fonts, state='readonly').grid(row=0, column=1, columnspan=3, sticky=tk.EW, pady=2)
        ttk.Label(config_frame, text="Impact字体:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(config_frame, textvariable=self.config_vars['impact_font'], values=self.available_impact_fonts, state='readonly').grid(row=1, column=1, columnspan=3, sticky=tk.EW, pady=2)
        ttk.Label(config_frame, text="消费税率(%):").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Entry(config_frame, textvariable=self.config_vars['tax_rate']).grid(row=2, column=1, columnspan=3, sticky=tk.EW, pady=2)
        res_frame = ttk.Frame(config_frame)
        res_frame.grid(row=3, column=0, columnspan=4, sticky=tk.EW)
        ttk.Label(res_frame, text="导出尺寸:").pack(side=tk.LEFT, pady=2)
        ttk.Entry(res_frame, textvariable=self.config_vars['export_width'], width=6).pack(side=tk.LEFT, padx=(5,0))
        ttk.Label(res_frame, text="x").pack(side=tk.LEFT, padx=2)
        ttk.Entry(res_frame, textvariable=self.config_vars['export_height'], width=6).pack(side=tk.LEFT)
        ttk.Button(res_frame, text="应用", command=self._update_canvas_size, style='TButton').pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(config_frame, text="定价加删除线", variable=self.config_vars['strikethrough']).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=2)
        ttk.Checkbutton(config_frame, text="显示边界线", variable=self.config_vars['show_border'], command=self.update_preview).grid(row=4, column=2, columnspan=2, sticky=tk.W, pady=2)
        color_frame = ttk.Frame(config_frame)
        color_frame.grid(row=5, column=0, columnspan=4, sticky=tk.EW, pady=(5,0))
        ttk.Button(color_frame, text="更改价格区底色", command=self.choose_color).pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.color_swatch = tk.Label(color_frame, text="■", fg=self.config_vars['price_area_color'].get(), font=('Helvetica', 14, 'bold'))
        self.color_swatch.pack(side=tk.LEFT, padx=5)
        config_frame.grid_columnconfigure(1, weight=1)
        pos_frame = ttk.LabelFrame(controls_frame, text="排版微调 (可按住Ctrl多选拖动)", padding=10)
        pos_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=5)
        add_custom_button = ttk.Button(pos_frame, text="添加自定义文本 (+)", command=self.add_custom_text_field)
        add_custom_button.pack(fill=tk.X, pady=(0, 5))
        pos_canvas_container = ttk.Frame(pos_frame)
        pos_canvas_container.pack(fill=tk.BOTH, expand=True)
        pos_canvas = tk.Canvas(pos_canvas_container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(pos_canvas_container, orient="vertical", command=pos_canvas.yview)
        self.scrollable_frame = ttk.Frame(pos_canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: pos_canvas.configure(scrollregion=pos_canvas.bbox("all")))
        pos_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        pos_canvas.configure(yscrollcommand=scrollbar.set)
        self.pos_widgets = {}
        self.pos_row_frames = {}
        self._build_all_pos_rows()
        pos_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas_w = int(self.config_vars['export_width'].get())
        canvas_h = int(self.config_vars['export_height'].get())
        self.preview_canvas = tk.Canvas(preview_frame, bg=BACKGROUND_COLOR, width=canvas_w, height=canvas_h, highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.preview_canvas.bind("<ButtonPress-1>", self.on_press)
        self.preview_canvas.bind("<B1-Motion>", self.on_drag)
        self.preview_canvas.bind("<ButtonRelease-1>", self.on_release)
        self.preview_canvas.bind("<Motion>", self._update_cursor) # 新增：绑定鼠标移动事件
        self.root.bind_all("<Control-KeyPress>", self._on_ctrl_press)
        self.root.bind_all("<Control-KeyRelease>", self._on_ctrl_release)

    def _build_all_pos_rows(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.pos_widgets = {}
        self.pos_row_frames = {}
        hdr_frame = ttk.Frame(self.scrollable_frame)
        hdr_frame.grid(row=0, column=0, sticky='ew', pady=(0, 2))
        ttk.Label(hdr_frame, text="元素", font=('Helvetica', 10, 'bold'), width=9).pack(side=tk.LEFT, padx=2)
        ttk.Label(hdr_frame, text="内容", font=('Helvetica', 10, 'bold'), width=12).pack(side=tk.LEFT, padx=2)
        ttk.Label(hdr_frame, text="X", font=('Helvetica', 10, 'bold'), width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(hdr_frame, text="Y", font=('Helvetica', 10, 'bold'), width=5).pack(side=tk.LEFT, padx=2)
        ttk.Label(hdr_frame, text="字号/宽", font=('Helvetica', 10, 'bold'), width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(hdr_frame, text="排列", font=('Helvetica', 10, 'bold'), width=6).pack(side=tk.LEFT, padx=2)
        ttk.Label(hdr_frame, text="高/行距", font=('Helvetica', 10, 'bold'), width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(hdr_frame, text="操作", font=('Helvetica', 10, 'bold'), width=4).pack(side=tk.LEFT, padx=2)
        pos_labels_map = { "barcode": "条码", "cat1": "分类1", "code": "ID", "cat2": "分类2", "title": "品名", "list_price": "定价", "used_label": "USED", "tax_date_label": "税込", "tax_date_value": "日期", "release_date": "发售日", "price_breakdown": "价格明细", "final_price": "最终价" }
        all_keys = list(self.data['elements'].keys())
        for i, key in enumerate(all_keys, 1):
            if key in pos_labels_map:
                self._build_pos_row(key, pos_labels_map.get(key, "未知"), i)
            elif key.startswith("custom_text_"):
                self._build_pos_row(key, f"自定义_{key.split('_')[-1]}", i, is_custom=True)

    def _build_pos_row(self, key, label_text, row_index, is_custom=False):
        row_frame = ttk.Frame(self.scrollable_frame)
        row_frame.grid(row=row_index, column=0, sticky='ew', pady=1)
        self.pos_row_frames[key] = row_frame
        label = ttk.Label(row_frame, text=label_text, style='Normal.TLabel', width=9)
        label.pack(side=tk.LEFT, padx=2)
        self.pos_widgets[key] = {'label': label, 'widgets': []}
        content_frame = ttk.Frame(row_frame, width=12)
        content_frame.pack(side=tk.LEFT, padx=2)
        if is_custom:
            entry_content = ttk.Entry(content_frame, textvariable=self.vars[key], width=12)
            entry_content.pack(fill=tk.X)
        elif key != 'barcode':
            ttk.Label(content_frame, text="(上方编辑)", font=('Helvetica', 9, 'italic')).pack()
        entry_x = ttk.Entry(row_frame, textvariable=self.element_vars[key]['x'], width=5)
        entry_x.pack(side=tk.LEFT, padx=2)
        entry_y = ttk.Entry(row_frame, textvariable=self.element_vars[key]['y'], width=5)
        entry_y.pack(side=tk.LEFT, padx=2)
        if key == 'barcode':
            ttk.Entry(row_frame, textvariable=self.element_vars[key]['w'], width=5).pack(side=tk.LEFT, padx=2)
        else:
            ttk.Entry(row_frame, textvariable=self.element_vars[key]['font_size'], width=5).pack(side=tk.LEFT, padx=2)
        if key == 'barcode':
            ttk.Label(row_frame, text="", width=8).pack(side=tk.LEFT, padx=2)
        else:
            combo_v = ttk.Combobox(row_frame, textvariable=self.element_vars[key]['vertical'], values=["横排", "竖排"], width=6, state='readonly')
            combo_v.pack(side=tk.LEFT, padx=2)
            combo_v.bind('<<ComboboxSelected>>', lambda e, k=key: self.toggle_line_spacing_widget(k))
        if key == 'barcode':
            ttk.Entry(row_frame, textvariable=self.element_vars[key]['h'], width=5).pack(side=tk.LEFT, padx=2)
        else:
            entry_ls = ttk.Entry(row_frame, textvariable=self.element_vars[key]['line_spacing'], width=5)
            self.pos_widgets[key]['widgets'].append(entry_ls)
            self.toggle_line_spacing_widget(key)
        if is_custom:
            ttk.Button(row_frame, text="X", command=lambda k=key: self.remove_custom_text_field(k), width=3).pack(side=tk.LEFT, padx=2)
        else:
            ttk.Label(row_frame, text="", width=4).pack(side=tk.LEFT, padx=2)

    def add_custom_text_field(self):
        self.custom_text_counter += 1
        key = f"custom_text_{self.custom_text_counter}"
        text_val = f"自定义文本{self.custom_text_counter}"
        props = {"pos": (50, 50), "size": (0, 0), "font_size": 20, "tag": key, "anchor": "nw", "vertical": False, "line_spacing": 1.0}
        self.data['info'][key] = text_val
        self.data['elements'][key] = props
        self.vars[key] = tk.StringVar(value=text_val)
        self.element_vars[key] = {'x': tk.StringVar(value=str(props['pos'][0])), 'y': tk.StringVar(value=str(props['pos'][1])), 'w': tk.StringVar(value=str(props['size'][0])), 'h': tk.StringVar(value=str(props['size'][1])), 'font_size': tk.StringVar(value=str(props['font_size'])), 'line_spacing': tk.StringVar(value=str(props.get('line_spacing', 1.0))), 'vertical': tk.StringVar(value="竖排" if props.get('vertical') else "横排")}
        next_row_index = self.scrollable_frame.grid_size()[1]
        self._build_pos_row(key, f"自定义_{key.split('_')[-1]}", next_row_index, is_custom=True)
        self.update_preview()

    def remove_custom_text_field(self, key):
        if key in self.pos_row_frames:
            self.pos_row_frames[key].destroy()
            del self.pos_row_frames[key]
        for d in [self.data['info'], self.data['elements'], self.vars, self.element_vars, self.pos_widgets]:
            if key in d: del d[key]
        self.selection.discard(key)
        self._highlight_widget()
        self.update_preview()

    def _clear_all_custom_fields(self):
        keys_to_remove = [k for k in self.data['elements'] if k.startswith("custom_text_")]
        for key in keys_to_remove:
            if key in self.pos_row_frames: self.pos_row_frames[key].destroy()
            for d in [self.data['info'], self.data['elements'], self.vars, self.element_vars, self.pos_widgets, self.pos_row_frames]:
                if key in d: del d[key]
        self.custom_text_counter = 0

    def _on_ctrl_press(self, event): self.ctrl_pressed = True
    def _on_ctrl_release(self, event): self.ctrl_pressed = False

    def _update_canvas_size(self):
        try:
            w, h = int(self.config_vars['export_width'].get()), int(self.config_vars['export_height'].get())
            if w > 0 and h > 0:
                self.preview_canvas.config(width=w, height=h)
                self.update_preview()
            else: messagebox.showerror("尺寸错误", "宽度和高度必须是正整数。")
        except (ValueError, tk.TclError): messagebox.showerror("尺寸错误", "请输入有效的整数。")

    def choose_color(self):
        color_code = colorchooser.askcolor(title="选择底色")
        if color_code and color_code[1]:
            self.config_vars['price_area_color'].set(color_code[1])
            self.color_swatch.config(fg=color_code[1])
            self.update_preview()

    def toggle_line_spacing_widget(self, key):
        if not self.pos_widgets.get(key) or not self.pos_widgets[key]['widgets']: return
        entry_ls = self.pos_widgets[key]['widgets'][0]
        if self.element_vars[key]['vertical'].get() == "竖排": entry_ls.pack(side=tk.LEFT, padx=2)
        else: entry_ls.pack_forget()

    def update_preview(self):
        self.preview_canvas.delete("all")
        canvas_w, canvas_h = self.preview_canvas.winfo_width(), self.preview_canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            self.root.after(50, self.update_preview)
            return
        full_res_image, self.element_bboxes = self._generate_pillow_image()
        if not full_res_image: return
        export_w, export_h = full_res_image.width, full_res_image.height
        scale = min(canvas_w / export_w, canvas_h / export_h)
        self.preview_scale = scale
        new_w, new_h = int(export_w * scale), int(export_h * scale)
        preview_image = full_res_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        centered_preview_bg = Image.new('RGBA', (canvas_w, canvas_h), BACKGROUND_COLOR)
        self.preview_offset_x, self.preview_offset_y = (canvas_w - new_w) // 2, (canvas_h - new_h) // 2
        centered_preview_bg.paste(preview_image, (self.preview_offset_x, self.preview_offset_y))
        self.preview_tk_img = ImageTk.PhotoImage(centered_preview_bg)
        self.preview_canvas.create_image(0, 0, anchor='nw', image=self.preview_tk_img, tags="background_image")
        self._draw_selection_ui()

    def _draw_selection_ui(self):
        """绘制选择高亮或变换框"""
        self.preview_canvas.delete("selection_highlight")
        self.transform_handles.clear()
        if not self.selection or not hasattr(self, 'element_bboxes'): return

        # 当选中多个元素时，只显示简单的虚线框
        if len(self.selection) > 1:
            for key in self.selection:
                if key in self.element_bboxes:
                    bbox = self.element_bboxes[key]
                    scaled_bbox = ((bbox[0] * self.preview_scale) + self.preview_offset_x, (bbox[1] * self.preview_scale) + self.preview_offset_y, (bbox[2] * self.preview_scale) + self.preview_offset_x, (bbox[3] * self.preview_scale) + self.preview_offset_y)
                    self.preview_canvas.create_rectangle(scaled_bbox, outline=SELECTION_BORDER_COLOR, width=1, dash=(4, 2), tags="selection_highlight")
            return

        # 当只选中一个元素时，绘制带控制柄的变换框
        key = list(self.selection)[0]
        if key not in self.element_bboxes: return
        
        bbox = self.element_bboxes[key]
        x1, y1, x2, y2 = (bbox[0] * self.preview_scale) + self.preview_offset_x, (bbox[1] * self.preview_scale) + self.preview_offset_y, (bbox[2] * self.preview_scale) + self.preview_offset_x, (bbox[3] * self.preview_scale) + self.preview_offset_y
        
        # 绘制主边框
        self.preview_canvas.create_rectangle(x1, y1, x2, y2, outline=SELECTION_BORDER_COLOR, width=1, tags="selection_highlight")

        # 定义8个控制柄的位置和类型
        hs = self.handle_size / 2
        handles_def = {
            'tl': (x1 - hs, y1 - hs, x1 + hs, y1 + hs), 'tm': ((x1+x2)/2 - hs, y1 - hs, (x1+x2)/2 + hs, y1 + hs), 'tr': (x2 - hs, y1 - hs, x2 + hs, y1 + hs),
            'ml': (x1 - hs, (y1+y2)/2 - hs, x1 + hs, (y1+y2)/2 + hs), 'mr': (x2 - hs, (y1+y2)/2 - hs, x2 + hs, (y1+y2)/2 + hs),
            'bl': (x1 - hs, y2 - hs, x1 + hs, y2 + hs), 'bm': ((x1+x2)/2 - hs, y2 - hs, (x1+x2)/2 + hs, y2 + hs), 'br': (x2 - hs, y2 - hs, x2 + hs, y2 + hs),
        }

        for name, h_bbox in handles_def.items():
            # 存储在画布坐标系下的控制柄信息
            self.transform_handles[name] = h_bbox
            self.preview_canvas.create_rectangle(h_bbox, fill=SELECTION_BORDER_COLOR, outline='white', tags="selection_highlight")

    def _get_element_text(self, key, info, base_price, tax, total_price):
        if key.startswith("custom_text_"): return info.get(key, "")
        text_map = {'cat1': info['cat1'], 'code': f"{info['code']}", 'cat2': info['cat2'], 'title': info['title'], 'list_price': f"定価 ¥{int(info.get('list_price', 0)):,}", 'used_label': "USED", 'tax_date_label': "税込", 'tax_date_value': info['tax_date'], 'release_date': f"発売日 {info['sale_date']}", 'price_breakdown': f"(本体¥{base_price:,} + 税¥{tax:,})", 'final_price': f"¥{total_price:,}"}
        return text_map.get(key, "")
    
    def _highlight_widget(self):
        for key, value in self.pos_widgets.items():
            value['label'].configure(style='Highlight.TLabel' if key in self.selection else 'Normal.TLabel')

    def _update_cursor(self, event):
        """根据鼠标位置更新光标样式"""
        if self.transform_mode: return # 如果正在拖拽，不改变光标
        
        cursor = "arrow" # 默认光标
        if len(self.selection) == 1:
            key = list(self.selection)[0]
            # 检查是否在控制柄上
            for name, bbox in self.transform_handles.items():
                if bbox[0] <= event.x <= bbox[2] and bbox[1] <= event.y <= bbox[3]:
                    # 根据控制柄位置设置对应的光标
                    if name in ['tl', 'br']: cursor = "size_nw_se"
                    elif name in ['tr', 'bl']: cursor = "size_ne_sw"
                    elif name in ['tm', 'bm']: cursor = "size_ns"
                    elif name in ['ml', 'mr']: cursor = "size_we"
                    break
            else: # 如果不在任何控制柄上，检查是否在元素本身
                if key in self.element_bboxes:
                    bbox = self.element_bboxes[key]
                    scaled_bbox = ((bbox[0] * self.preview_scale) + self.preview_offset_x, (bbox[1] * self.preview_scale) + self.preview_offset_y, (bbox[2] * self.preview_scale) + self.preview_offset_x, (bbox[3] * self.preview_scale) + self.preview_offset_y)
                    if scaled_bbox[0] <= event.x <= scaled_bbox[2] and scaled_bbox[1] <= event.y <= scaled_bbox[3]:
                        cursor = "fleur" # 移动光标
        
        self.preview_canvas.config(cursor=cursor)

    def on_press(self, event):
        self.transform_mode = None
        # 检查是否点击了某个控制柄
        if len(self.selection) == 1:
            for name, bbox in self.transform_handles.items():
                if bbox[0] <= event.x <= bbox[2] and bbox[1] <= event.y <= bbox[3]:
                    self.transform_mode = name
                    self.active_handle = name
                    break
        
        # 如果没有点击控制柄，则执行原有的选择逻辑
        if not self.transform_mode:
            click_x = (event.x - self.preview_offset_x) / self.preview_scale
            click_y = (event.y - self.preview_offset_y) / self.preview_scale
            clicked_key = None
            for key, bbox in reversed(list(self.element_bboxes.items())):
                if bbox[0] <= click_x <= bbox[2] and bbox[1] <= click_y <= bbox[3]:
                    clicked_key = key
                    break
            if not self.ctrl_pressed:
                if clicked_key not in self.selection: self.selection.clear()
            if clicked_key:
                if clicked_key in self.selection:
                    if self.ctrl_pressed: self.selection.remove(clicked_key)
                else: self.selection.add(clicked_key)
            else:
                if not self.ctrl_pressed: self.selection.clear()
            
            if self.selection: self.transform_mode = 'move'

        # 存储拖拽起始数据
        self._drag_data['x'], self._drag_data['y'] = event.x, event.y
        self._drag_data['items'] = {}
        for key in self.selection:
            try:
                props = self.data['elements'][key]
                self._drag_data['items'][key] = {
                    'x': int(self.element_vars[key]['x'].get()), 'y': int(self.element_vars[key]['y'].get()),
                    'w': int(self.element_vars[key]['w'].get()), 'h': int(self.element_vars[key]['h'].get()),
                    'font_size': int(self.element_vars[key]['font_size'].get()),
                    'original_bbox': self.element_bboxes.get(key)
                }
            except (ValueError, KeyError, tk.TclError): pass

        self._highlight_widget()
        self._draw_selection_ui()

    def on_drag(self, event):
        if not self.transform_mode or not self.selection: return
        key = list(self.selection)[0]
        start_data = self._drag_data['items'][key]
        dx = (event.x - self._drag_data['x']) / self.preview_scale
        dy = (event.y - self._drag_data['y']) / self.preview_scale

        if self.transform_mode == 'move':
            for k in self.selection:
                s_data = self._drag_data['items'][k]
                self.element_vars[k]['x'].set(str(round(s_data['x'] + dx)))
                self.element_vars[k]['y'].set(str(round(s_data['y'] + dy)))
        else: # 处理缩放
            orig_w = start_data['original_bbox'][2] - start_data['original_bbox'][0]
            orig_h = start_data['original_bbox'][3] - start_data['original_bbox'][1]
            if orig_w == 0 or orig_h == 0: return

            # 根据拖动的控制柄计算新的宽高
            new_w, new_h = orig_w, orig_h
            if 'l' in self.transform_mode: new_w -= dx
            if 'r' in self.transform_mode: new_w += dx
            if 't' in self.transform_mode: new_h -= dy
            if 'b' in self.transform_mode: new_h += dy

            # 对于角点拖拽，保持宽高比
            if len(self.transform_mode) == 2:
                ratio = orig_w / orig_h
                if abs(new_w / orig_w) > abs(new_h / orig_h):
                    new_h = new_w / ratio
                else:
                    new_w = new_h * ratio
            
            # 更新数据
            if key == 'barcode':
                self.element_vars[key]['w'].set(str(max(10, round(new_w))))
                self.element_vars[key]['h'].set(str(max(10, round(new_h))))
            else: # 更新文本字号
                scale_factor = new_h / orig_h
                new_font_size = max(5, round(start_data['font_size'] * scale_factor))
                self.element_vars[key]['font_size'].set(str(new_font_size))
        
        # 拖拽时不完全重绘，只更新UI输入框，由on_release最后完成重绘
        # 可以在这里画一个临时的变换框预览，但为了简化，暂时省略

    def on_release(self, event):
        if self.transform_mode:
            self.update_preview() # 拖拽或缩放结束后，进行一次完整的重绘
        self.transform_mode = None
        self.active_handle = None
        self._drag_data = {}
        self.preview_canvas.config(cursor="arrow") # 恢复默认光标

    def save_template(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON模板", "*.json")], title="保存模板")
        if not filepath: return
        for key, props in self.data['elements'].items():
            try:
                props['pos'] = (int(self.element_vars[key]['x'].get()), int(self.element_vars[key]['y'].get()))
                props['size'] = (int(self.element_vars[key]['w'].get()), int(self.element_vars[key]['h'].get()))
                props['font_size'] = int(self.element_vars[key]['font_size'].get())
                props['vertical'] = self.element_vars[key]['vertical'].get() == "竖排"
                if props.get('vertical'): props['line_spacing'] = float(self.element_vars[key]['line_spacing'].get())
            except (ValueError, tk.TclError, KeyError):
                messagebox.showerror("错误", f"元素 '{key}' 的值无效。")
                return
        template_data = {"info": {k: v.get() for k, v in self.vars.items()}, "config": {k: v.get() for k, v in self.config_vars.items()}, "elements": self.data['elements']}
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("成功", f"模板已保存到:\n{filepath}")
        except Exception as e: messagebox.showerror("保存失败", f"无法保存模板: {e}")

    def load_template(self):
        filepath = filedialog.askopenfilename(filetypes=[("JSON模板", "*.json")], title="载入模板")
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            self._clear_all_custom_fields()
            self.data['elements'] = template_data.get("elements", {})
            self.data['info'] = template_data.get("info", {})
            for key, value in template_data.get("config", {}).items():
                if key in self.config_vars: self.config_vars[key].set(value)
            self.vars = {key: tk.StringVar(value=str(val)) for key, val in self.data['info'].items()}
            self.element_vars = { key: {'x': tk.StringVar(value=str(val['pos'][0])), 'y': tk.StringVar(value=str(val['pos'][1])), 'w': tk.StringVar(value=str(val['size'][0])), 'h': tk.StringVar(value=str(val['size'][1])), 'font_size': tk.StringVar(value=str(val['font_size'])), 'line_spacing': tk.StringVar(value=str(val.get('line_spacing', 1.0))), 'vertical': tk.StringVar(value="竖排" if val.get('vertical') else "横排")} for key, val in self.data['elements'].items()}
            self._build_all_pos_rows()
            self.color_swatch.config(fg=self.config_vars['price_area_color'].get())
            self._update_canvas_size()
            messagebox.showinfo("成功", "模板加载完毕！")
        except Exception as e:
            messagebox.showerror("加载失败", f"无法解析模板: {e}")
            self.init_data()
            self._build_all_pos_rows()
            self.update_preview()

    def export_as_image(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG图像", "*.png")], title="导出为图片", initialfile=f"{self.vars['code'].get()}_sticker.png")
        if not filepath: return
        image, _ = self._generate_pillow_image()
        if not image:
            messagebox.showerror("导出失败", "无法生成图像。")
            return
        try:
            image.save(filepath, 'PNG')
            messagebox.showinfo("成功", f"贴纸已导出到:\n{filepath}")
        except Exception as e: messagebox.showerror("导出失败", f"保存图片时出错: {e}")
            
    def _generate_pillow_image(self):
        try:
            export_width, export_height = int(self.config_vars['export_width'].get()), int(self.config_vars['export_height'].get())
        except (ValueError, tk.TclError):
            messagebox.showerror("尺寸错误", "导出尺寸无效。")
            return None, None
        image = Image.new('RGBA', (export_width, export_height), BACKGROUND_COLOR)
        draw = ImageDraw.Draw(image)
        element_bboxes = {}
        draw.rectangle([(20, 200), (export_width - 20, export_height - 20)], fill=self.config_vars['price_area_color'].get())
        if self.config_vars['show_border'].get():
            draw.rectangle([(0, 0), (export_width - 1, export_height - 1)], outline="gray", width=1)
        info = {k: v.get() for k, v in self.vars.items()}
        try:
            base_price = int(info.get('used_price_base', 0))
            tax_rate = self.config_vars['tax_rate'].get() / 100
            tax = math.floor(base_price * tax_rate)
            total_price = base_price + tax
        except (ValueError, tk.TclError): base_price, tax, total_price = 0, 0, 0
        sorted_elements = sorted(self.data['elements'].items(), key=lambda item: 0 if item[0] == 'barcode' else 1)
        for key, props in sorted_elements:
            try:
                x, y = int(self.element_vars[key]['x'].get()), int(self.element_vars[key]['y'].get())
                if key != 'barcode':
                    font_size = int(self.element_vars[key]['font_size'].get())
                    if font_size <= 0: continue
                    font_family_name = self.config_vars['impact_font'].get() if key in ['used_label', 'final_price'] else self.config_vars['jp_font'].get()
                    text_to_draw = self._get_element_text(key, info, base_price, tax, total_price)
                    fill_color = "gray" if key == 'list_price' else "black"
                    is_vertical = self.element_vars[key]['vertical'].get() == "竖排"
                    anchor = props.get('anchor', 'nw')
                    bbox = self._draw_text_on_image(draw, key, x, y, text_to_draw, font_family_name, font_size, fill_color, anchor, is_vertical)
                    if bbox: element_bboxes[key] = bbox
                else:
                    bbox = self._draw_barcode_on_image(image, key, x, y, info)
                    if bbox: element_bboxes[key] = bbox
            except Exception as e: print(f"导出元素'{key}'时出错: {e}")
        return image, element_bboxes

    def _draw_text_on_image(self, draw, key, x, y, text, font_family, font_size, fill, anchor, is_vertical):
        anchor_map = { "n": "mt", "ne": "rt", "e": "rm", "se": "rb", "s": "mb", "sw": "lb", "w": "lm", "nw": "lt", "center": "mm" }
        pil_anchor = anchor_map.get(anchor, "lt")
        font_path = self.font_map.get(font_family)
        try:
            current_font = ImageFont.truetype(font_path if font_path else font_family, font_size)
        except (IOError, OSError):
            fallback_path = self.font_map.get(self.available_jp_fonts[0]) if self.available_jp_fonts else None
            try: current_font = ImageFont.truetype(fallback_path, font_size) if fallback_path else ImageFont.load_default()
            except (IOError, OSError): current_font = ImageFont.load_default()
        if not is_vertical:
            bbox = draw.textbbox((x, y), text, font=current_font, anchor=pil_anchor)
            draw.text((x, y), text, font=current_font, fill=fill, anchor=pil_anchor)
            if key == 'list_price' and self.config_vars['strikethrough'].get():
                draw.line([(bbox[0], (bbox[1]+bbox[3])/2), (bbox[2], (bbox[1]+bbox[3])/2)], fill=fill, width=2)
            return bbox
        else:
            try: line_spacing_multiplier = float(self.element_vars[key]['line_spacing'].get())
            except (ValueError, tk.TclError): line_spacing_multiplier = 1.0
            line_height = font_size * line_spacing_multiplier
            total_height = (len(text) - 1) * line_height
            start_y = y
            if 's' in anchor: start_y = y - total_height
            elif 'center' in anchor or 'm' in pil_anchor: start_y = y - total_height / 2
            overall_bbox = [float('inf'), float('inf'), float('-inf'), float('-inf')]
            for i, char in enumerate(text):
                char_y = start_y + i * line_height
                char_pil_anchor = "m" + pil_anchor[1] 
                char_bbox = draw.textbbox((x, char_y), char, font=current_font, anchor=char_pil_anchor)
                draw.text((x, char_y), char, font=current_font, fill=fill, anchor=char_pil_anchor)
                overall_bbox[0], overall_bbox[1] = min(overall_bbox[0], char_bbox[0]), min(overall_bbox[1], char_bbox[1])
                overall_bbox[2], overall_bbox[3] = max(overall_bbox[2], char_bbox[2]), max(overall_bbox[3], char_bbox[3])
            return tuple(overall_bbox)

    def _draw_barcode_on_image(self, image, key, x, y, info):
        barcode_content = info.get('barcode_data', '')
        if not barcode_content: return None
        try:
            w, h = int(self.element_vars[key]['w'].get()), int(self.element_vars[key]['h'].get())
            if w <= 0 or h <= 0: return None
            EAN = barcode.get_barcode_class('code128')
            buffer = io.BytesIO()
            options = {'module_height': 15.0, 'quiet_zone': 2.0, 'write_text': False}
            EAN(barcode_content, writer=ImageWriter()).write(buffer, options=options)
            buffer.seek(0)
            barcode_img = Image.open(buffer).convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)
            paste_x, paste_y = int(x - w / 2), int(y - h / 2)
            image.paste(barcode_img, (paste_x, paste_y), barcode_img)
            return (paste_x, paste_y, paste_x + w, paste_y + h)
        except Exception as e:
            print(f"导出条码时出错: {e}")
            return None

if __name__ == '__main__':
    try:
        import PIL, barcode
    except ImportError:
        messagebox.showerror("依赖缺失", "请先安装必要的库: pip install Pillow python-barcode")
        sys.exit(1)
    root = tk.Tk()
    app = StickerGenerator(root)
    root.mainloop()
