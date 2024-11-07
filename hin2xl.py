from pdf2image import convert_from_path
import os
import cv2
import numpy as np
from PIL import Image
import pytesseract
import re
import csv
from google.cloud import vision
import io
import time
from google.api_core.exceptions import ServiceUnavailable
from googletrans import Translator
from ai4bharat.transliteration import XlitEngine


e = XlitEngine(src_script_type="indic", beam_width=10)
def transliterate_hin2eng(text):
    out = e.translit_sentence(text,lang_code="hi")
    return out.upper()

def detect_text_tesseract(img):
    text = pytesseract.image_to_string(img,lang='eng+hin')
    return text

translator = Translator()
def translate(text):
    translation = translator.translate(text, src='hi', dest='en')
    return translation.text.upper()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = './gcp_key.json'
client = vision.ImageAnnotatorClient()
def detect_text_google(content):
    try:
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        texts = response.text_annotations
        text = texts[0].description
        return text
    except ServiceUnavailable:
        return detect_text_google(image)   


def contains_special_characters(s):
    pattern = re.compile(r'[^A-Za-z\s]')
    return bool(pattern.search(s))

def main(pdf_path,bbox):
    parts = os.path.normpath(pdf_path).split(os.sep)
    part = parts[-1]
    assembly = parts[-2]
    district = parts[-3]
    state = parts[-4]

    images = convert_from_path(pdf_path, dpi=230)

    page1image = images[0]
    page1_img_byte_arr = io.BytesIO()
    page1image.save(page1_img_byte_arr, format='JPEG')
    p1_content = page1_img_byte_arr.getvalue()
    image_bytes = io.BytesIO(p1_content)
    with Image.open(image_bytes) as img:
        image_np = np.array(img)
        cropped_image_np = image_np[bbox[1]:bbox[3], bbox[0]:bbox[2]]
        cropped_image = Image.fromarray(cropped_image_np)
        img_byte_arr = io.BytesIO()
        cropped_image.save(img_byte_arr, format='JPEG')
        content = img_byte_arr.getvalue()
        txt = detect_text_google(content).replace(':\n',': NA\n')+'\n'
        if 'मुख्य शहर / गाँव\nडाकघर\nपुलिस स्टेशन\nकानूनगो\nतहसील\nजिला\nपिन कोड' in txt:
            pattern = re.compile(r':\s*(.*?)\n')
            page1data = re.findall(pattern,txt)
            if len(page1data) != 7:
                return 0
            vl = translate(page1data[0])
            po = translate(page1data[1])
            ps = translate(page1data[2])
            ka = translate(page1data[3])
            th = translate(page1data[4])
            pc = page1data[6]
        else:
            return 0


    card_count = 0
    for image in images[2:-1]:
        page_text = detect_text_tesseract(image)

        section_pattern = re.compile(r'अनुभाग संख्या एवं नाम\s*:\s*(.*?)\n')
        section = re.findall(section_pattern,page_text)
        if not section:
            section_ = ''
        else:
           section_ = translate(section[0])

        image_np = np.array(image)
        image_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        bounding_boxes = [cv2.boundingRect(c) for c in contours]
        contours_sorted = sorted(contours, key=lambda c: (cv2.boundingRect(c)[1], cv2.boundingRect(c)[0]))
        for contour in contours_sorted:
            x, y, w, h = cv2.boundingRect(contour)
            if 608 > w > 588 and 253 > h > 233:
                card_count += 1
                card = image_bgr[y:y+h, x:x+w]
                card_image = Image.fromarray(cv2.cvtColor(card, cv2.COLOR_BGR2RGB))
                
                def clean_data_write_csv(text,lib):
                    name_pattern = re.compile(r'निर्वाचक का नाम\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')
                    spouse_pattern = re.compile(r'(पिता का नाम|माता का नाम|अन्य|पति का नाम)\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')
                    house_pattern = re.compile(r'मकान संख्या\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)(\n|फोटो उपलब्ध)')
                    age_pattern = re.compile(r'उम्र\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(\d+)\s')
                    gender_pattern = re.compile(r'(लिंग|लिंग)\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')

                    sp_dict = {
                        'पिता का नाम':"Father's Name",
                        'माता का नाम':"Mother's Name",
                        'पति का नाम':"Husband's Name",
                        'अन्य':"Others"
                    }

                    ge_dict = {
                        'पुरुष':'M',
                        'महिला':'F'
                    }

                    try:
                        name = transliterate_hin2eng(re.findall(name_pattern,text)[0][1])
                        spouse = sp_dict[re.findall(spouse_pattern,text)[0][0]]
                        spouse_name = transliterate_hin2eng(re.findall(spouse_pattern,text)[0][2])
                        house = transliterate_hin2eng(re.findall(house_pattern,text)[0][1])
                        age = int(re.findall(age_pattern,text)[0][1])
                        gender = ge_dict[re.findall(gender_pattern,text)[0][2]]
                    except Exception as e:
                        if lib == 'free':
                            img_byte_arr = io.BytesIO()
                            card_image.save(img_byte_arr, format='JPEG')
                            content = img_byte_arr.getvalue()
                            text = detect_text_google(content)
                            return clean_data_write_csv(text,'paid')
                        else:
                            print(e)
                            return False


                    if (age < 18) or (age >100) or (contains_special_characters(name)) or (contains_special_characters(spouse_name)) or (gender not in ['M','F']):
                        if lib == 'free':
                            img_byte_arr = io.BytesIO()
                            card_image.save(img_byte_arr, format='JPEG')
                            content = img_byte_arr.getvalue()
                            text = detect_text_google(content)
                            return clean_data_write_csv(text,'paid')
                        else:
                            return False

                    row = [state,district,assembly,part,vl,po,ps,ka,th,pc,section_,card_count,name,spouse,spouse_name,house,age,gender]
                    print(row,lib)
                    try:
                        with open(f'./data/{assembly}.csv','a',newline='',encoding='utf-8') as f:
                            csv_writer = csv.writer(f)
                            csv_writer.writerow(row)
                        return True
                    except:
                        return False
                    
                text = detect_text_tesseract(card_image)
                status = clean_data_write_csv(text,'free')
                if status == False:
                    if ('लिंग' in text):
                        row = [state,district,assembly,part,card_count]
                    else:
                        row = [state,district,assembly,part,card_count,'DELETED']
                    try:
                        with open('./data/errors.csv','a',newline='',encoding='utf-8') as err:
                            csv_writer = csv.writer(err)
                            csv_writer.writerow(row)
                    except:
                        pass
                    


with open('./data/errors.csv','a',newline='',encoding='utf-8') as err:
    csv_writer = csv.writer(err)
    heading = ['State','District','Assembly','Part Detail','Card No.']
    csv_writer.writerow(heading)


src = './src'
bbox = [
            int(809.1),           #xmin
            int(921.47),          #ymin
            int(1026.11+809.1),   #xmax
            int(464.63+921.47)    #ymax
        ]

for root,dirs,files in os.walk(src):
    for file in files:
        if file.endswith('.pdf'):
            if 'completed_files' not in root:
                pdf_path = os.path.join(root,file)
                parts = os.path.normpath(pdf_path).split(os.sep)
                assembly = parts[-2]
                with open(f'./data/{assembly}.csv','a',newline='',encoding='utf-8') as f:
                    csv_writer = csv.writer(f)
                    heading = ['State','District','Assembly','Part Detail','Main Town or Village','Post Office','Police Station','Kanoongo','Tehsil','Pincode','Section','Card No.','Name','Spouse Relation','Spouse Name','House No.','Age','Gender']
                    csv_writer.writerow(heading)
                o = main(pdf_path,bbox)
                if o != 0:
                    with open('./data/done.txt','a',encoding='utf-8') as f:
                        f.write(pdf_path+'\n')
