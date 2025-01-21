import geopandas as gpd
import folium
from folium import GeoJson
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import webbrowser
import os

class PopulationViewer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("서울시 생활인구 조회 시스템")
        
        # 창 크기 설정 (너비x높이+x좌표+y좌표)
        window_width = 850
        window_height = 1000
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = 0  # 화면 최상단에 위치
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.resizable(True, True)  # 사용자가 창 크기를 조절할 수 있도록 설정
        
        # 메인 캔버스와 스크롤바 생성
        self.canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        # 마우스 휠 이벤트 바인딩
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # 스크롤바와 캔버스 배치
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.shp_path = None
        self.csv_path = None
        
        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('TLabel', padding=5)
        
        self.create_widgets()
        
    def create_widgets(self):
        # 제목
        title_label = ttk.Label(
            self.scrollable_frame, 
            text="서울시 생활인구 조회 시스템",
            font=('맑은 고딕', 36, 'bold')
        )
        title_label.pack(pady=20)
        
        # 데이터 선택 프레임
        data_frame = ttk.LabelFrame(self.scrollable_frame, text="데이터 파일 선택", padding=10)
        data_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Button(
            data_frame, 
            text="지도 데이터 선택 (집계구.shp)",
            command=self.load_shp
        ).pack(fill='x', pady=5)
        
        ttk.Button(
            data_frame, 
            text="생활인구 데이터 선택 (csv)",
            command=self.load_csv
        ).pack(fill='x', pady=5)
        
        # 지도 열기 버튼 - scrollable_frame으로 변경
        ttk.Button(
            self.scrollable_frame,  # self.root에서 변경
            text="지도 열기 (마우스를 올려서 집계구 코드 확인)",
            command=self.show_map
        ).pack(pady=10, padx=20, fill='x')  # fill='x' 추가
        
        # 집계구 코드 입력 프레임
        code_frame = ttk.LabelFrame(self.scrollable_frame, text="집계구 코드 입력", padding=10)
        code_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(
            code_frame,
            text="지도에서 확인한 집계구 코드를 입력해주세요\n(여러 개인 경우 쉼표로 구분)",
            font=('맑은 고딕', 28)
        ).pack(pady=5)
        
        self.code_entry = ttk.Entry(
            code_frame,
            width=30,
            font=('맑은 고딕', 28)
        )
        self.code_entry.pack(pady=10)
        
        # 시간 선택 프레임
        time_frame = ttk.LabelFrame(
            self.scrollable_frame, 
            text="시간 선택 (0-23시)", 
            padding=10
        )
        time_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(
            time_frame,
            text="원하시는 시간을 선택해주세요",
            font=('맑은 고딕', 28)
        ).pack(pady=5)
        
        self.time_var = tk.StringVar()
        time_combo = ttk.Combobox(
            time_frame, 
            textvariable=self.time_var,
            values=[f"{i:02d}:00" for i in range(24)] + ["하루치 보기"],  # 하루치 보기 추가
            width=30,
            font=('맑은 고딕', 28),
            state='readonly'
        )
        time_combo.pack(pady=10)
        time_combo.set("하루치 보기")  # 기본값 설정
        
        ttk.Label(
            time_frame,
            text="예시: 13:00 = 오후 1시",
            font=('맑은 고딕', 25),
            foreground='gray'
        ).pack()
        
        # 조회 버튼 - scrollable_frame으로 변경
        ttk.Button(
            self.scrollable_frame,  # self.root에서 변경
            text="조회하기",
            command=self.check_population,
            style='Query.TButton'
        ).pack(pady=15, padx=20, fill='x')  # fill='x' 추가
        
        # 결과 프레임
        result_frame = ttk.LabelFrame(self.scrollable_frame, text="조회 결과", padding=10)
        result_frame.pack(fill='x', padx=20, pady=10)
        
        self.result_label = ttk.Label(
            result_frame, 
            text="집계구 코드를 입력하고 시간을 선택한 후\n조회 버튼을 클릭해주세요",
            font=('맑은 고딕', 28),
            justify='center'
        )
        self.result_label.pack(pady=10)

    def show_map(self):
        if not self.shp_path:
            messagebox.showerror("오류", "지도 데이터를 먼저 선택해주세요.")
            return
            
        try:
            geo = gpd.read_file(self.shp_path)
            geo = geo[['TOT_REG_CD', 'geometry']]
            if geo.crs is None:
                geo = geo.set_crs(epsg=5179)
            geo = geo.to_crs(epsg=4326)
            geo['geometry'] = geo['geometry'].simplify(tolerance=0.001)

            m = folium.Map(
                location=[37.5665, 126.9780],
                zoom_start=11,
                tiles='cartodbpositron',
                prefer_canvas=True
            )

            GeoJson(
                geo,
                style_function=lambda x: {
                    'fillColor': 'white',
                    'color': '#666666',
                    'weight': 0.3,
                    'fillOpacity': 0.1
                },
                highlight_function=lambda x: {
                    'color': '#ff0000',
                    'weight': 1,
                    'fillOpacity': 0.3
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['TOT_REG_CD'],
                    aliases=['집계구코드:'],
                    style="font-size: 25px; padding: 5px;"
                )
            ).add_to(m)

            output_file = 'seoul_map_simple.html'
            m.save(output_file)
            webbrowser.open('file://' + os.path.realpath(output_file))
            
        except Exception as e:
            messagebox.showerror("오류", f"지도 생성 중 오류가 발생했습니다.\n{str(e)}")

    def check_population(self):
        if not self.csv_path:
            messagebox.showerror("오류", "생활인구 데이터를 먼저 선택해주세요.")
            return
        
        try:
            # 입력된 코드들을 쉼표로 구분하여 리스트로 변환
            target_codes = [code.strip() for code in self.code_entry.get().split(',')]
            if not target_codes or all(not code for code in target_codes):
                messagebox.showwarning("경고", "집계구 코드를 입력해주세요.")
                return
            
            selected_time = self.time_var.get()
            
            # 선택된 시간대 처리
            if selected_time == "하루치 보기":
                target_hours = range(24)  # 0시부터 23시까지
            else:
                target_hours = [int(selected_time.split(':')[0])]  # 선택된 시간대
            
            data = pd.read_csv(self.csv_path, encoding='cp949')
            
            # 모든 입력된 코드에 대한 데이터 필터링
            result = data[
                (data['집계구코드'].astype(str).isin(target_codes)) & 
                (data['시간대구분'].isin(target_hours))  # 선택된 시간대에 따라 필터링
            ]
            
            if len(result) > 0:
                total_population = result['총생활인구수'].sum()
                
                # 하루치 보기일 경우, 선택된 집계구 수를 그대로 사용
                if selected_time == "하루치 보기":
                    codes_found = len(target_codes)  # 선택된 집계구 수
                else:
                    codes_found = len(result)  # 특정 시간대의 집계구 개수
                
                self.result_label.config(
                    text=f"[조회 완료]\n\n"
                         f"총 생활인구: {total_population:.2f}명\n"
                         f"(조회된 집계구: {codes_found}개)"
                )
            else:
                self.result_label.config(
                    text="해당하는 데이터가 없습니다.\n"
                         "집계구 코드를 다시 확인해주세요."
                )
                
        except Exception as e:
            messagebox.showerror("오류", f"조회 중 오류가 발생했습니다.\n{str(e)}")

    def load_shp(self):
        self.shp_path = filedialog.askopenfilename(
            title="지도 데이터 선택",
            filetypes=[("Shape 파일", "*.shp")]
        )
        if self.shp_path:
            messagebox.showinfo("알림", "지도 데이터가 선택되었습니다.")

    def load_csv(self):
        self.csv_path = filedialog.askopenfilename(
            title="생활인구 데이터 선택",
            filetypes=[("CSV 파일", "*.csv")]
        )
        if self.csv_path:
            messagebox.showinfo("알림", "생활인구 데이터가 선택되었습니다.")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = PopulationViewer()
    app.run()