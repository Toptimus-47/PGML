# PGML_Editor.py
# PilGi_Markup_Language_Integrated_Editor
# License = GPLv3

import tkinter as tk
from tkinter import scrolledtext, font, messagebox, filedialog
import re
import os
import sys

import reportlab.lib.pagesizes as pagesizes
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, Color

class MarkupEditor:
    # 사전 정의된 색상 맵 (대소문자 무시)
    PREDEFINED_COLORS = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255)
    }

    def __init__(self, root):
        self.root = root
        self.root.title("필기용 마크업 에디터")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)

        self.current_file_path = None # 현재 편집 중인 파일 경로
        self.modified = False # 문서 수정 여부 플래그

        # 사용할 기본 글꼴 설정 (시스템 폰트 사용)
        self.base_font_size = 12
        
        preferred_font_names = ["나눔스퀘어 네오 Regular"]
        self.base_font_family = "TkDefaultFont" # 기본 fallback 폰트 설정
        
        # 시스템에 설치된 폰트 목록 확인
        available_fonts = font.families()

        # "나눔스퀘어 네오"를 최우선으로 직접 확인하고 할당합니다.
        if "나눔스퀘어 네오" in available_fonts:
            self.base_font_family = "나눔스퀘어 네오"
        else:
            # "나눔스퀘어 네오" (한글 이름)가 직접 발견되지 않으면,
            # preferred_font_names에 있는 다른 이름들을 순서대로 확인합니다.
            for name in preferred_font_names:
                if name in available_fonts:
                    self.base_font_family = name
                    break
        
        # 이제 self.base_font_family는 찾은 최적의 글꼴 또는 "TkDefaultFont"를 가집니다.
        self.base_font = font.Font(family=self.base_font_family, size=self.base_font_size)

        # 기본 fallback 폰트가 사용된 경우 사용자에게 경고 메시지를 표시합니다.
        if self.base_font_family == "TkDefaultFont":
            messagebox.showwarning("글꼴 경고", f"선호하는 글꼴 ({', '.join(preferred_font_names)})을 시스템에서 찾을 수 없습니다. 기본 글꼴로 대체됩니다.")
            
        # PDF export를 위한 폰트 등록
        try:
            pdfmetrics.registerFont(TTFont('NanumSquareNeo', 'NanumSquareNeo-Regular.ttf'))
            pdfmetrics.registerFont(TTFont('NanumSquareNeo-Bold', 'NanumSquareNeo-Bold.ttf'))
            # 만약 NanumSquare Neo-Italic.ttf 파일이 있다면 아래 줄의 주석을 해제하세요:
            # pdfmetrics.registerFont(TTFont('NanumSquareNeo-Italic', 'NanumSquareNeo-Italic.ttf'))
        except Exception as e:
            messagebox.showwarning("PDF 글꼴 경고", f"PDF 내보내기를 위한 글꼴을 등록할 수 없습니다. PDF에서 글꼴이 다르게 표시될 수 있습니다: {e}\n'NanumSquareNeo-Regular.ttf' 및 'NanumSquareNeo-Bold.ttf' 파일이 스크립트와 동일한 폴더에 있는지 확인해주세요.")

        # UI 요소 설정
        self.setup_ui()

        # 태그 설정 함수 호출 (UI 요소 생성 후)
        self.tag_config_setup()

        # 이벤트 바인딩
        self.bind_events()

    def setup_ui(self):
        # 미리보기 텍스트 위젯 (왼쪽에 배치)
        self.preview_text = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, font=(self.base_font_family, self.base_font_size)
        )
        self.preview_text.pack(expand=True, fill="both", side="left", padx=5, pady=5)
        self.preview_text.config(state=tk.DISABLED) # 미리보기는 편집 불가

        # 텍스트 에디터 (오른쪽에 배치)
        self.text_editor = scrolledtext.ScrolledText(
            self.root, wrap=tk.WORD, font=(self.base_font_family, self.base_font_size)
        )
        self.text_editor.pack(expand=True, fill="both", side="right", padx=5, pady=5)
        self.text_editor.bind("<<Modified>>", self.on_text_modified)

        # 메뉴 바
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="새로 만들기", command=self.new_document)
        file_menu.add_command(label="열기", command=self.open_document)
        file_menu.add_command(label="저장", command=self.save_document)
        file_menu.add_command(label="다른 이름으로 저장", command=self.save_document_as)
        file_menu.add_command(label="PDF로 내보내기", command=self.export_to_pdf)
        file_menu.add_separator()
        file_menu.add_command(label="끝내기", command=self.root.quit)

    def bind_events(self):
        # 텍스트 편집기 내용 변경 감지
        self.text_editor.bind("<KeyRelease>", self.update_preview_delayed)
        # Ctrl+S 단축키 바인딩
        self.root.bind("<Control-s>", lambda event: self.save_document())
        self.root.bind("<Control-S>", lambda event: self.save_document()) # 대문자 S도 처리 (Shift + s)

    def on_text_modified(self, event=None):
        self.modified = True
        self.root.title(f"필기용 마크업 에디터 - {os.path.basename(self.current_file_path) if self.current_file_path else '제목 없음'}*")
        self.text_editor.edit_modified(False) # 수정 플래그 리셋

    def update_preview_delayed(self, event=None):
        # 짧은 지연 후 미리보기 업데이트를 예약하여 불필요한 업데이트 방지
        if hasattr(self, '_after_id'):
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(200, self.update_preview) # 200ms 지연

    def update_preview(self):
        raw_text = self.text_editor.get("1.0", tk.END)
        # 미리보기 처리를 위해 각주 및 헤더를 임시 태그로 변환
        processed_text_for_preview = self.process_markup_for_preview(raw_text)
        self.apply_styles_to_preview(processed_text_for_preview)

    def process_markup_for_preview(self, text):
        temp_footnotes = {}
        temp_fn_counter = 0

        # <fn> 태그를 [N]으로 변환하고 각주 내용을 저장
        fn_pattern = r'<fn(?:\s+type\((?:normal)\))?>(.*?)</fn>'
        
        offset = 0
        processed_text_parts = []
        
        for match in re.finditer(fn_pattern, text, flags=re.DOTALL | re.IGNORECASE):
            temp_fn_counter += 1
            fn_number = temp_fn_counter
            
            # 각주 내용 추출 (inner_content)
            inner_content = match.group(1).strip()
            # 각주 유형도 함께 저장 (display_type 결정에 사용될 수 있음)
            fn_type = match.group(2) if match.group(2) else "normal" # Default to "normal" if type not specified
            temp_footnotes[fn_number] = (inner_content, fn_type)

            # 현재 매치 이전의 텍스트 추가
            processed_text_parts.append(text[offset:match.start()])
            # [N] 형태로 변환하여 추가
            processed_text_parts.append(f"[{fn_number}]")
            
            offset = match.end()
            
        processed_text_parts.append(text[offset:])
        text_with_footnotes_replaced = "".join(processed_text_parts)

        # 헤더 처리 (H1-H6)
        # 줄의 시작에 #이 있거나, 이전 줄이 빈 줄이고 현재 줄이 #으로 시작하는 경우를 포함
        header_pattern = r'^(#+)(?!#)(.*)$'
        def replace_header(match):
            hashes = match.group(1)
            content = match.group(2).strip()
            level = min(len(hashes), 6) # H1에서 H6까지만 지원
            # HTML 태그 대신 임시 PGML_HEADER 태그 사용
            return f"<HEADER_H{level}>{content}</HEADER_H{level}>"

        processed_text_with_headers = re.sub(
            header_pattern, replace_header, text_with_footnotes_replaced, flags=re.MULTILINE
        )

        # 각주 내용을 전역으로 접근 가능하게 저장 (미리보기에서 렌더링되지 않으므로 필요)
        self.preview_footnotes_data = temp_footnotes # 각주 번호와 (내용, 유형)을 저장

        return processed_text_with_headers

    def apply_styles_to_preview(self, text_content):
        # 기존 태그 제거
        self.preview_text.config(state=tk.NORMAL) # 수정 가능하도록 임시 변경
        self.preview_text.tag_remove("all", "1.0", tk.END)
        self.preview_text.delete("1.0", tk.END) # 모든 텍스트 삭제

        active_tags_set = set() # 현재 활성화된 스타일 태그를 저장하는 집합
        current_pos = 0

        # PGML 스타일 태그 (C, HL 포함), 각주 번호, 헤더 태그
        # 그룹 1: 열린 태그 (<B>, <I>, <C(...)>, <HL> 등)
        # 그룹 3: 범용 닫는 태그 (</TC>)
        # 그룹 4: 각주 번호 ([N])
        # 그룹 5: 헤더 시작 (<HEADER_Hn>)
        # 그룹 6: 헤더 끝 (</HEADER_Hn>)
        style_regex = re.compile(
            r'(<(?:B|굵게|I|기울임|UL|밑줄|CL|가운뎃줄|HL|C(?:\s*=\s*\w+|=?\s*#?[\da-f]{3,6}|(?:\(\s*(?:\d{1,3}|)\s*,\s*(?:\d{1,3}|)\s*,\s*(?:\d{1,3}|)\s*(?:,\s*(?:\d{1,3}|)\s*)?\)))\s*)+>)' # 그룹 1: 열린 태그 (내부 태그명은 그룹 2)
            r'|(</TC>)' # 그룹 2: 범용 닫는 태그
            r'|(\[\d+\])' # 그룹 3: 각주 번호 [N]
            r'|(<HEADER_H[1-6]>)' # 그룹 4: 헤더 시작 (임시 태그)
            r'|(</HEADER_H[1-6]>)' # 그룹 5: 헤더 끝 (임시 태그)
            , re.DOTALL | re.IGNORECASE
        )

        # C, HL 태그 내 속성을 파싱하기 위한 정규식 (이전과 동일)
        attribute_regex = re.compile(
            r'(B|굵게)|(I|기울임)|(UL|밑줄)|(CL|가운뎃줄)|(HL)' # 그룹 1-5: B, I, UL, CL, HL
            r'|(C)\s*' # 그룹 6: C
            r'(?:=\s*(\w+)' # 그룹 7: 색상명 (예: =red)
            r'|(?:\(\s*#?([\da-f]{3,6})\s*\))' # 그룹 8: 16진수 HEX (예: (#FF0000))
            r'|(?:\(\s*(\d{1,3}|)\s*,\s*(\d{1,3}|)\s*,\s*(\d{1,3}|)\s*(?:,\s*(?:\d{1,3}|)\s*)?\))' # 그룹 9-12: CMYK (C,M,Y,K) (0값 생략 가능)
            r'|(?:\(\s*(\d{1,3}|)\s*,\s*(\d{1,3}|)\s*,\s*(\d{1,3}|)\s*\)))' # 그룹 13-15: RGB (R,G,B) (0값 생략 가능)
            , re.IGNORECASE
        )

        self.preview_text.config(state=tk.NORMAL) # 텍스트 삽입을 위해 임시 활성화

        for match in style_regex.finditer(text_content):
            if match.start() > current_pos:
                # 현재 매치 이전의 텍스트 삽입
                text_segment = text_content[current_pos:match.start()]
                self.preview_text.insert(tk.END, text_segment, tuple(active_tags_set))

            # 열린 태그 처리 (그룹 1)
            if match.group(1): 
                inner_tag_content = match.group(1).strip('<> ') # 예: "B I", "C=red"
                
                # 중첩된 여러 태그 처리 (예: <B I>)
                for attr_match in attribute_regex.finditer(inner_tag_content):
                    if attr_match.group(1): # B or 굵게
                        active_tags_set.add("bold")
                    elif attr_match.group(2): # I or 기울임
                        active_tags_set.add("italic")
                    elif attr_match.group(3): # UL or 밑줄
                        active_tags_set.add("underline")
                    elif attr_match.group(4): # CL or 가운뎃줄
                        active_tags_set.add("strikethrough")
                    elif attr_match.group(5): # HL
                        active_tags_set.add("highlight")
                    elif attr_match.group(6): # C (색상)
                        color_name_or_hex = attr_match.group(7) # 색상명 (예: =red)
                        hex_value = attr_match.group(8) # HEX 값 (예: (#FF0000))
                        # CMYK 또는 RGB 값 처리 (그룹 9-12)
                        cmyk_or_rgb_values = tuple(filter(None, attr_match.groups()[8:])) # 모든 가능한 숫자 그룹

                        color_tag = None
                        color_hex = None

                        if color_name_or_hex:
                            color_rgb = self.PREDEFINED_COLORS.get(color_name_or_hex.lower())
                            if color_rgb:
                                color_hex = f"#{color_rgb[0]:02x}{color_rgb[1]:02x}{color_rgb[2]:02x}"
                        elif hex_value:
                            if len(hex_value) == 3:
                                hex_value = ''.join([c*2 for c in hex_value])
                            color_hex = f"#{hex_value}"
                        elif cmyk_or_rgb_values:
                            try:
                                parsed_values = []
                                for v in cmyk_or_rgb_values:
                                    try:
                                        parsed_values.append(int(v))
                                    except ValueError:
                                        # Invalid literal for int, default to 0
                                        parsed_values.append(0) 
                                
                                if len(parsed_values) == 4: # CMYK (C, M, Y, K)
                                    c, m, y, k = parsed_values
                                    # CMYK를 RGB로 변환 (ReportLab은 CMYK 직접 지원 안함, Tkinter도 마찬가지)
                                    r = int(255 * (1 - c/100) * (1 - k/100))
                                    g = int(255 * (1 - m/100) * (1 - k/100))
                                    b = int(255 * (1 - y/100) * (1 - k/100))
                                    color_hex = f"#{r:02x}{g:02x}{b:02x}"
                                elif len(parsed_values) == 3: # RGB (R, G, B)
                                    r, g, b = parsed_values
                                    color_hex = f"#{r:02x}{g:02x}{b:02x}"
                            except Exception: # Catch any other potential errors during parsing
                                pass # Silently fail color parsing if format is totally off
                        
                        if color_hex:
                            color_tag = f"color_{color_hex.upper()}" # 태그 이름은 대문자로 통일
                            self.preview_text.tag_config(color_tag, foreground=color_hex)
                            active_tags_set.add(color_tag)

            # 범용 닫는 태그 처리 (그룹 2)
            elif match.group(2): 
                # 모든 일반적인 글꼴/하이라이트/가운뎃줄/색상 태그 제거
                all_span_tags = {"bold", "italic", "underline", "strikethrough", "highlight"}
                active_tags_set.difference_update(all_span_tags)

                # 모든 색상 태그 제거
                current_color_tags = [tag for tag in active_tags_set if tag.startswith("color_")]
                for tag in current_color_tags:
                    active_tags_set.discard(tag)

            elif match.group(3): # 각주 번호 [N]
                try:
                    footnote_number = int(match.group(3).strip('[]'))
                    footnote_text_display = match.group(3)

                    if footnote_number in self.preview_footnotes_data:
                        footnote_content, footnote_type = self.preview_footnotes_data[footnote_number]
                        
                        # 각주 번호 링크 태그
                        link_tag = f"fn_link_{footnote_number}"
                        self.preview_text.tag_config(link_tag, foreground="blue", underline=True)
                        
                        # 삽입
                        self.preview_text.insert(tk.END, footnote_text_display, (link_tag,))
                        
                        # 클릭 이벤트 바인딩
                        self.preview_text.tag_bind(link_tag, "<Button-1>", lambda e, num=footnote_number: self.scroll_to_preview_fn_location(num))
                        self.preview_text.tag_bind(link_tag, "<Enter>", lambda e: self.preview_text.config(cursor="hand2"))
                        self.preview_text.tag_bind(link_tag, "<Leave>", lambda e: self.preview_text.config(cursor="arrow"))
                    else:
                        # 데이터에 없는 각주 번호는 일반 텍스트로
                        self.preview_text.insert(tk.END, footnote_text_display)
                except ValueError:
                    # If footnote number is invalid, insert as plain text without special formatting
                    self.preview_text.insert(tk.END, match.group(3))
                current_pos = match.end()
                continue # 각주 번호는 텍스트로 삽입되었으므로 다음 루프 진행

            elif match.group(4): # 헤더 시작 <HEADER_Hn>
                try:
                    header_level = int(match.group(4)[len('<HEADER_H'):-1]) # 예: <HEADER_H1> -> 1
                    end_of_header_tag = f"</HEADER_H{header_level}>"
                    end_of_header_tag_match = text_content.find(end_of_header_tag, match.end())

                    if end_of_header_tag_match != -1:
                        header_text = text_content[match.end():end_of_header_tag_match].strip()
                        header_tag = f"header_h{header_level}"
                        self.preview_text.insert(tk.END, header_text + "\n", (header_tag,)) # 헤더 뒤에 개행 추가
                        current_pos = end_of_header_tag_match + len(end_of_header_tag)
                        continue # 헤더는 전체를 처리했으므로 다음 루프 진행
                    else: # Mismatched header tag (should not happen with internal tags)
                        self.preview_text.insert(tk.END, match.group(4)) # Insert tag as plain text
                        current_pos = match.end()
                        continue
                except ValueError:
                    # If header level is invalid, insert as plain text without special formatting
                    self.preview_text.insert(tk.END, match.group(4))
                    current_pos = match.end()
                    continue

            current_pos = match.end()

        # 마지막 텍스트 세그먼트 처리
        if current_pos < len(text_content):
            text_segment = text_content[current_pos:]
            self.preview_text.insert(tk.END, text_segment, tuple(active_tags_set))

        # 각주 목록 표시
        if hasattr(self, 'preview_footnotes_data') and self.preview_footnotes_data:
            self.preview_text.insert(tk.END, "\n\n---\n각주 목록:\n", "separator")
            
            # 각주 번호 순서대로 정렬
            sorted_footnotes_items = sorted(self.preview_footnotes_data.items())
            
            for fn_num, (fn_content, fn_type) in sorted_footnotes_items:
                footnote_list_text = f"[{fn_num}] {fn_content}\n"
                
                # 각주 목록 항목도 링크로 만들 수 있음 (선택 사항)
                self.preview_text.insert(tk.END, footnote_list_text, "footnote_list_item") # 일반 텍스트로 삽입
                # 각주 목록 항목 자체는 링크가 필요 없으므로 단순 삽입

        self.preview_text.config(state=tk.DISABLED) # 미리보기 편집 불가로 재설정

    def tag_config_setup(self):
        # 기본 폰트 객체는 __init__에서 생성됨
        
        # 굵게
        self.preview_text.tag_config("bold", font=(self.base_font_family, self.base_font_size, "bold"))
        # 기울임
        self.preview_text.tag_config("italic", font=(self.base_font_family, self.base_font_size, "italic"))
        # 밑줄
        self.preview_text.tag_config("underline", underline=True)
        # 가운뎃줄
        self.preview_text.tag_config("strikethrough", overstrike=True)
        # 형광펜 (배경색으로 구현)
        self.preview_text.tag_config("highlight", background="yellow")

        # 헤더 스타일
        self.preview_text.tag_config("header_h1", font=(self.base_font_family, 24, "bold"), spacing3=10) # spacing3은 단락 뒤 간격
        self.preview_text.tag_config("header_h2", font=(self.base_font_family, 20, "bold"), spacing3=8)
        self.preview_text.tag_config("header_h3", font=(self.base_font_family, 16, "bold"), spacing3=6)
        self.preview_text.tag_config("header_h4", font=(self.base_font_family, 14, "bold"), spacing3=4)
        self.preview_text.tag_config("header_h5", font=(self.base_font_family, 13, "bold"), spacing3=3)
        self.preview_text.tag_config("header_h6", font=(self.base_font_family, 12, "bold"), spacing3=2)

        # 각주 구분선 스타일
        self.preview_text.tag_config("separator", font=(self.base_font_family, self.base_font_size, "bold"), spacing1=10, spacing3=5)


    def process_markup_for_pdf_export(self, text):
        temp_footnotes_for_pdf = {}
        temp_fn_counter = 0

        # <fn> 태그를 [N]으로 변환하고 각주 내용을 저장
        fn_pattern = r'<fn(?:\s+type\((?:normal)\))?>(.*?)</fn>'
        
        offset = 0
        processed_text_parts = []
        
        for match in re.finditer(fn_pattern, text, flags=re.DOTALL | re.IGNORECASE):
            temp_fn_counter += 1
            fn_number = temp_fn_counter
            
            # 각주 내용 추출 (inner_content)
            inner_content = match.group(1).strip()
            temp_footnotes_for_pdf[fn_number] = inner_content

            # 현재 매치 이전의 텍스트 추가
            processed_text_parts.append(text[offset:match.start()])
            # [N] 형태로 변환하여 추가
            processed_text_parts.append(f"[{fn_number}]")
            
            offset = match.end()
            
        processed_text_parts.append(text[offset:])
        text_with_footnotes_replaced = "".join(processed_text_parts)

        # 헤더 처리 (H1-H6)
        # 단일 '#'으로 시작하는 줄을 헤더로 처리
        header_pattern = r'^(#+)(?!#)(.*)$'
        def replace_header_for_pdf(match):
            hashes = match.group(1)
            content = match.group(2).strip()
            level = min(len(hashes), 6) # H1에서 H6까지만 지원
            # HTML 태그로 변환
            return f"<h{level}>{content}</h{level}>"

        processed_text_with_headers = re.sub(
            header_pattern, replace_header_for_pdf, text_with_footnotes_replaced, flags=re.MULTILINE
        )

        self.footnotes_for_pdf_export = temp_footnotes_for_pdf # PDF 내보내기를 위한 각주 저장

        return processed_text_with_headers

    def convert_pgml_to_reportlab_html(self, pgml_text):
        # 1. 일반적인 글꼴 태그 변환
        replacements = {
            r'<B>': '<b>', r'<굵게>': '<b>',
            r'<I>': '<i>', r'<기울임>': '<i>',
            r'<UL>': '<u>', r'<밑줄>': '<u>',
            r'<CL>': '<strike>', r'<가운뎃줄>': '<strike>',
            r'<HL>': '<font backColor="yellow">', # ReportLab은 backColor 사용
        }
        for pgml_tag, html_tag in replacements.items():
            pgml_text = re.sub(re.escape(pgml_tag), html_tag, pgml_text, flags=re.IGNORECASE)

        # 2. 색상 태그 (<C>) 변환
        color_tag_pattern = re.compile(
            r'<C(?:\s*=\s*(\w+))?' # 그룹 1: 색상명 (예: =red)
            r'(?:\s*=\s*#?([\da-f]{3,6}))?' # 그룹 2: 16진수 HEX (예: =#FF0000 또는 =FFF)
            r'(?:\(\s*#?([\da-f]{3,6})\s*\))?' # 그룹 3: 16진수 HEX (예: (#FF0000) 또는 (FFF))
            r'(?:\(\s*(\d{1,3}|)\s*,\s*(\d{1,3}|)\s*,\s*(\d{1,3}|)\s*(?:,\s*(?:\d{1,3}|)\s*)?\))?' # 그룹 4-7: CMYK (C,M,Y,K) 또는 RGB (R,G,B)
            r'>', re.IGNORECASE
        )

        def replace_color_tag(match):
            color_name = match.group(1)
            hex_value1 = match.group(2)
            hex_value2 = match.group(3)
            cmyk_or_rgb_values = tuple(filter(None, match.groups()[3:])) # CMYK 또는 RGB 값 튜플

            color_code = None

            if color_name:
                # 사전 정의된 색상명 처리
                rgb = self.PREDEFINED_COLORS.get(color_name.lower())
                if rgb:
                    color_code = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            elif hex_value1 or hex_value2:
                # 16진수 HEX 처리
                hex_val = hex_value1 if hex_value1 else hex_value2
                if len(hex_val) == 3: # 3자리 HEX를 6자리로 확장
                    hex_val = ''.join([c*2 for c in hex_val])
                color_code = f"#{hex_val}"
            elif cmyk_or_rgb_values:
                # CMYK 또는 RGB 처리
                try:
                    parsed_values = []
                    for v in cmyk_or_rgb_values:
                        try:
                            parsed_values.append(int(v))
                        except ValueError:
                            # Invalid literal for int, default to 0
                            parsed_values.append(0) 
                    
                    if len(parsed_values) == 4: # CMYK
                        c, m, y, k = parsed_values
                        # CMYK를 RGB로 변환 (ReportLab은 CMYK 직접 지원 안함)
                        # 간단한 근사치 변환
                        r = int(255 * (1 - c/100) * (1 - k/100))
                        g = int(255 * (1 - m/100) * (1 - k/100))
                        b = int(255 * (1 - y/100) * (1 - k/100))
                        color_code = f"#{r:02x}{g:02x}{b:02x}"
                    elif len(parsed_values) == 3: # RGB
                        r, g, b = parsed_values
                        color_code = f"#{r:02x}{g:02x}{b:02x}"
                except Exception:
                    pass # 잘못된 숫자 형식 무시

            if color_code:
                return f'<font color="{color_code}">'.lower() # 소문자로 변환
            return '' # 매치되었으나 유효한 색상 코드 없는 경우 빈 문자열 반환

        pgml_text = color_tag_pattern.sub(replace_color_tag, pgml_text)

        # 3. 닫는 태그 변환
        # </TC>는 ReportLab HTML에서 모든 열린 태그를 한 번에 닫는 것은 불가능하므로,
        # 예상되는 모든 HTML 닫는 태그를 넣어줌. 순서는 중요하지 않음.
        # 실제 ReportLab은 텍스트 파싱 중 열린 태그만 유효하게 닫음.
        pgml_text = re.sub(r'</TC>', '</font></b></i></strike><u>', pgml_text, flags=re.IGNORECASE)

        return pgml_text

    def export_to_pdf(self):
        if not self.current_file_path:
            messagebox.showwarning("경고", "먼저 문서를 저장해 주세요.")
            return

        # 저장된 파일 경로에서 .pml 확장자를 .pdf로 변경
        pdf_file_path = os.path.splitext(self.current_file_path)[0] + ".pdf"

        # PDF 문서 생성
        doc = SimpleDocTemplate(
            pdf_file_path,
            pagesize=pagesizes.A4,
            rightMargin=50, leftMargin=50,
            topMargin=50, bottomMargin=50
        )
        
        story = []
        raw_text = self.text_editor.get("1.0", tk.END)

        # PDF 내보내기용으로 마크업 처리 (헤더, 각주 등)
        processed_text_for_pdf = self.process_markup_for_pdf_export(raw_text)

        # PGML 스타일을 ReportLab HTML 스타일로 변환
        reportlab_html_content = self.convert_pgml_to_reportlab_html(processed_text_for_pdf)

        # 스타일 시트 설정
        styles = getSampleStyleSheet()
        
        # 기본 스타일
        style = styles['Normal']
        style.fontName = 'NanumSquareNeo'
        style.fontSize = 12
        style.leading = 14 # 줄 간격

        # 볼드 스타일을 위한 폰트 설정
        styles['Bold'].fontName = 'NanumSquareNeo-Bold'
        
        # 이탤릭 스타일을 위한 폰트 설정 (NanumSquareNeo-Italic.ttf가 없는 경우 일반 폰트 사용)
        # 만약 'NanumSquareNeo-Italic.ttf' 폰트 파일이 있다면, '__init__'에서 등록 후 아래 줄을 'NanumSquareNeo-Italic'으로 변경하세요.
        styles['Italic'].fontName = 'NanumSquareNeo' 

        # 밑줄 및 가운뎃줄은 기본 폰트와 함께 ReportLab 태그로 처리됨
        styles['Underline'].fontName = 'NanumSquareNeo'
        styles['Strike'].fontName = 'NanumSquareNeo'

        # 헤더 스타일 설정
        for i in range(1, 7):
            header_style = styles[f'h{i}']
            header_style.fontName = 'NanumSquareNeo-Bold' # 헤더는 볼드 폰트 사용
            header_style.fontSize = 24 - (i * 2) # h1=22, h2=20 등
            header_style.leading = header_style.fontSize + 2
            header_style.spaceAfter = 10 # 헤더 아래 공간

        # ReportLab Paragraph 객체 생성
        # convert_pgml_to_reportlab_html이 변환한 HTML 마크업을 Paragraph가 해석
        try:
            p = Paragraph(reportlab_html_content, style)
            story.append(p)
        except Exception as e:
            messagebox.showerror("PDF 변환 오류", f"PDF 내용 변환 중 오류가 발생했습니다: {e}\n마크업을 확인해주세요.")
            print(f"PDF Paragraph 생성 오류: {e}")
            return
        
        # 각주 목록 추가
        if hasattr(self, 'footnotes_for_pdf_export') and self.footnotes_for_pdf_export:
            story.append(Spacer(1, 0.2 * pagesizes.cm)) # 여백 추가
            story.append(Paragraph("---<br/><b>각주 목록:</b>", styles['Normal'])) # 각주 목록 제목
            for fn_num, fn_content in sorted(self.footnotes_for_pdf_export.items()):
                # 각주 원본 텍스트를 Paragraph로 추가
                fn_text = f"[{fn_num}] {fn_content}"
                story.append(Paragraph(fn_text, styles['Normal']))
        
        # PDF 빌드
        try:
            doc.build(story)
            messagebox.showinfo("내보내기 완료", f"PDF 파일이 성공적으로 생성되었습니다:\n{pdf_file_path}")
            self.modified = False
        except Exception as e:
            messagebox.showerror("PDF 저장 오류", f"PDF 파일을 저장하는 중 오류가 발생했습니다: {e}\n폰트 파일 존재 여부 및 경로를 확인해주세요.")
            print(f"PDF build 오류: {e}")


    def new_document(self):
        if self.modified:
            if messagebox.askyesno("저장", "변경 사항을 저장하시겠습니까?"):
                self.save_document()
        self.text_editor.delete("1.0", tk.END)
        self.current_file_path = None
        self.modified = False
        self.root.title("필기용 마크업 에디터 - 제목 없음")
        self.update_preview() # 미리보기 업데이트

    def open_document(self):
        if self.modified:
            if messagebox.askyesno("저장", "변경 사항을 저장하시겠습니까?"):
                self.save_document()
        file_path = filedialog.askopenfilename(
            defaultextension=".pml", # .pml을 기본 확장자로 설정
            filetypes=[("PGML 파일", "*.pml"), ("PGML 파일 (대체)", "*.pgml"), ("모든 파일", "*.*")] # .pml과 .pgml 모두 지원
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    loaded_content = file.read()
                
                # '--- 각주 목록:'을 기준으로 본문과 각주 섹션을 분리
                parts = re.split(r'(---\s*각주 목록:\s*)', loaded_content, flags=re.IGNORECASE, maxsplit=1)
                main_body = parts[0].strip() # 본문 내용 (원래 <fn> 태그 포함)

                self.text_editor.delete("1.0", tk.END)
                self.text_editor.insert("1.0", main_body)
                self.current_file_path = file_path
                self.modified = False
                self.root.title(f"필기용 마크업 에디터 - {os.path.basename(file_path)}")
                self.update_preview() # 로드된 본문을 기반으로 미리보기 업데이트
            except FileNotFoundError:
                messagebox.showerror("오류", "파일을 찾을 수 없습니다.")
            except Exception as e:
                messagebox.showerror("불러오기 오류", f"문서 불러오기 중 오류가 발생했습니다: {e}")

    def save_document(self):
        if self.current_file_path:
            self._save_to_file(self.current_file_path)
        else:
            self.save_document_as()

    def save_document_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pml", # .pml을 기본 확장자로 설정
            filetypes=[("PGML 파일", "*.pml"), ("PGML 파일 (대체)", "*.pgml"), ("모든 파일", "*.*")] # .pml과 .pgml 모두 지원
        )
        if file_path:
            self._save_to_file(file_path)

    def _save_to_file(self, file_path):
        raw_text = self.text_editor.get("1.0", tk.END)
        # 저장 시에는 미리보기에서 변환된 태그를 다시 원래 PGML <fn> 태그로 복원 (각주 목록 제외)
        text_to_save = self.process_markup_for_save(raw_text)

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(text_to_save)
            self.current_file_path = file_path
            self.modified = False
            self.root.title(f"필기용 마크업 에디터 - {os.path.basename(file_path)}")
            messagebox.showinfo("저장 완료", "문서가 성공적으로 저장되었습니다.")
        except Exception as e:
            messagebox.showerror("저장 오류", f"문서 저장 중 오류가 발생했습니다: {e}")

    def process_markup_for_save(self, text):
        temp_footnotes_for_save = {}
        fn_pattern = re.compile(r'<fn(?:\s+type\((?:normal)\))?>(.*?)</fn>', re.DOTALL | re.IGNORECASE)
        fn_counter = 0

        # Find all footnotes in the original text and extract their *inner content*
        for match in fn_pattern.finditer(text):
            fn_counter += 1
            # 각주 내용만 저장하며, <fn> 태그는 저장될 본문에 그대로 유지됨
            temp_footnotes_for_save[fn_counter] = match.group(1).strip() 

        final_content_to_save = text.strip() # Start with the exact content from the editor, strip trailing whitespace

        if fn_counter > 0: # If footnotes were found
            generated_footnote_list_section = "\n\n---\n각주 목록:\n"
            # Append each footnote as "[N] Content"
            for fn_num, fn_content in sorted(temp_footnotes_for_save.items()):
                generated_footnote_list_section += f"[{fn_num}] {fn_content}\n"
            final_content_to_save += generated_footnote_list_section
        
        return final_content_to_save

    def scroll_to_preview_fn_location(self, fn_number):
        # 각주 본문 [N] 클릭 시 미리보기에서 해당 각주 목록으로 이동
        # 이 함수는 현재 Preview 텍스트 위젯에 실제 각주 목록이 있을 때 작동합니다.
        # 각주 목록의 시작점을 찾습니다.
        start_of_footnotes_section = self.preview_text.search("---\n각주 목록:\n", "1.0", tk.END, nocase=True)
        if not start_of_footnotes_section:
            return 

        # 각주 목록 내 해당 번호의 텍스트를 찾습니다.
        # 예: "[1] 이것은 첫 번째 각주입니다."
        target_text = f"[{fn_number}]"
        
        # 각주 목록 섹션 내에서만 검색하도록 범위 지정
        target_index = self.preview_text.search(target_text, start_of_footnotes_section, tk.END, nocase=True)

        if target_index:
            self.preview_text.see(target_index) # 해당 위치로 스크롤
            
            # 하이라이트 효과 (일시적으로 적용)
            self.preview_text.tag_remove("highlight_fn", "1.0", tk.END) # 기존 하이라이트 제거
            self.preview_text.tag_add("highlight_fn", target_index, f"{target_index} lineend")
            self.preview_text.tag_config("highlight_fn", background="yellow", foreground="black")
            
            # 1초 후 하이라이트 제거
            self.root.after(1000, lambda: self.preview_text.tag_remove("highlight_fn", "1.0", tk.END))


# 메인 애플리케이션 실행
if __name__ == "__main__":
    root = tk.Tk()
    editor = MarkupEditor(root)
    root.mainloop()