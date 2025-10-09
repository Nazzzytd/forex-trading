import os
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ocr_pdf_to_text(pdf_path, output_dir):
    """将PDF转换为可搜索文本"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 获取PDF文件名（不含扩展名）
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_file = os.path.join(output_dir, f"{pdf_name}_ocr.txt")
    
    try:
        logger.info(f"开始OCR处理: {pdf_path}")
        
        # 将PDF转换为图片
        images = convert_from_path(pdf_path)
        
        all_text = []
        for i, image in enumerate(images):
            logger.info(f"处理第 {i+1}/{len(images)} 页")
            
            # 使用OCR识别文本
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            all_text.append(f"--- 第 {i+1} 页 ---\n{text}\n")
        
        # 保存文本
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_text))
        
        logger.info(f"OCR完成，文本已保存到: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"OCR处理失败: {str(e)}")
        return None

if __name__ == "__main__":
    pdf_path = "trade_docs/日本蜡烛图技术.pdf"
    ocr_pdf_to_text(pdf_path, "ocr_output")