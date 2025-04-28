import fitz  # PyMuPDF

def crop_pdf(input_pdf_path, output_pdf_path, page_num, crop_rect):
    try:
        doc = fitz.open(input_pdf_path)
    except Exception as e:
        print(f"打開 PDF 文件失敗: {e}")
        return

    total_pages = len(doc)
    print(f"該 PDF 檔案有 {total_pages} 頁")

    if page_num is None:
        new_doc = fitz.open()
        for i in range(total_pages):
            page = doc.load_page(i)
            page_width, page_height = page.rect.width, page.rect.height

            # 限制 crop_rect 在頁面範圍內
            left = max(crop_rect[0], 0)
            top = max(crop_rect[1], 0)
            right = min(crop_rect[2], page_width)
            bottom = min(crop_rect[3], page_height)

            page.set_cropbox(fitz.Rect(left, top, right, bottom))
            new_doc.insert_pdf(doc, from_page=i, to_page=i)

        try:
            new_doc.save(output_pdf_path)
            print(f"✅ PDF 全部裁切完成，輸出: {output_pdf_path}")
        except Exception as e:
            print(f"❌ 儲存失敗: {e}")
        return

    # 裁切單頁的情況
    if page_num < 0 or page_num >= total_pages:
        print("頁面號碼無效")
        return

    page = doc.load_page(page_num)
    page_width, page_height = page.rect.width, page.rect.height
    print(f"該頁面大小: {page.rect}")

    left = max(crop_rect[0], 0)
    top = max(crop_rect[1], 0)
    right = min(crop_rect[2], page_width)
    bottom = min(crop_rect[3], page_height)

    page.set_cropbox(fitz.Rect(left, top, right, bottom))

    new_doc = fitz.open()
    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    new_doc.save(output_pdf_path)
    print(f"✅ 單頁裁切完成，輸出: {output_pdf_path}")
    
input_pdf_path = "07植物的故事.pdf"
output_pdf_path = "output_cropped_upper.pdf"
crop_rect = (0, 0, 230, 130)  # 裁切左上角 (0, 100) 到右下角 (249.84, 368)
page_num = None  # None 表示整本處理

crop_pdf(input_pdf_path, output_pdf_path, page_num, crop_rect)    
