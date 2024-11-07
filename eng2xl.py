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


def detect_text_tesseract(img):
    text = pytesseract.image_to_string(img)
    return text


os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = './gcp_key.json'
def detect_text_google(image):
    try:
        client = vision.ImageAnnotatorClient()
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        content = buffered.getvalue()
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        texts = response.text_annotations
        return texts[0].description
    except ServiceUnavailable:
        return detect_text_google(image)   


def contains_special_characters(s):
    pattern = re.compile(r'[^A-Za-z\s]')
    return bool(pattern.search(s))



def main(pdf_path):
    parts = os.path.normpath(pdf_path).split(os.sep)
    part = parts[-1]
    # assembly = parts[-2]
    district = parts[-3]
    state = parts[-4]

    try:
        images = convert_from_path(pdf_path, dpi=230)
    except Exception as e:
        print(e)
        return 0

    page1text = detect_text_tesseract(images[0])

    vill = re.compile(r'Main Town or Village\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')
    wd = re.compile(r'Ward\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')
    po = re.compile(r'Post Office\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')
    ps = re.compile(r'Police Station\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')
    th = re.compile(r'Tahsil\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')
    # mn = re.compile(r'Mandal\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')
    
    # rd = re.compile(r'Revenue Division\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')
    pc = re.compile(r'Pin code\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(\d+)\n')

    try:
        vill_ = re.findall(vill,page1text)[0][1].replace('!','I').replace('|','I')
    except:
        print('Village')
        return 0
        # vill_ = input(f'Enter Village for {part}: ')

    try:
        wd_ = re.findall(wd,page1text)[0][1].replace('!','I').replace('|','I')
    except:
        print('Ward')
        return 0
        # wd_ = input(f'Enter Ward for {part}: ')

    try:
        po_ = re.findall(po,page1text)[0][1].replace('!','I').replace('|','I')
    except:
        print('Post Office')
        return 0
        # po_ = input(f'Enter Post office for {part}: ')

    try:
        ps_ = re.findall(ps,page1text)[0][1].replace('!','I').replace('|','I')
    except:
        print('Police station')
        return 0
        # ps_ = input(f'Enter Police station for {part}: ')

    try:
        th_ = re.findall(th,page1text)[0][1].replace('!','I').replace('|','I')
    except:
        print('Tehsil')
        return 0
        # th_ = input(f'Enter Police station for {part}: ')

    # try:
    #     mn_ = re.findall(mn,page1text)[0][1]
    # except:
    #     mn_ = input(f'Enter Mandal for {part}: ')

    # try:
    #     rd_ = re.findall(rd,page1text)[0][1]
    # except:
    #     rd_ = input(f'Enter Revenue division for {part}: ')

    try:
        pc_ = re.findall(pc,page1text)[0][1][-6:]
    except:
        print('Pincode')
        return 0
        # pc_ = input(f'Enter Pincode for {part}: ')




    card_count = 0
    for image in images[2:-1]:
        page_text = detect_text_tesseract(image)

        section_pattern = re.compile(r'Section No and Name\s*(.*?)\n')
        section = re.findall(section_pattern,page_text)
        if not section:
            section = ['']

        assembly_pattern = re.compile(r'Assembly Constituency No and Name\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)(\n|Part No.)')
        assembly = re.findall(assembly_pattern,page_text)
        if not assembly:
            assembly = [('','')]

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

                # rest = {
                #     '1 - DODIPUTTU' : [i for i in range(360,791)]
                # }

                # if part not in rest:
                #     continue
                # if card_count not in rest[part]:
                #     continue
                

                def clean_data_write_csv(text,lib):
                    name_pattern = re.compile(r'Name\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')
                    spouse_pattern = re.compile(r'(Fathers Name|Mothers Name|Others|Husbands Name)\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')
                    house_pattern = re.compile(r'House Number\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)(\n|\s)')
                    age_pattern = re.compile(r'Age\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(\d+)\s')
                    gender_pattern = re.compile(r'(Gender|Gander)\s*(!|\+:|\+|:|>|=|\*|\?|\s|-|#|;|t|¢)\s*(.*?)\n')

                    try:
                        name = re.findall(name_pattern,text)[0][1].replace('!','I').replace('|','I')
                        spouse = re.findall(spouse_pattern,text)[0][0]
                        spouse_name = re.findall(spouse_pattern,text)[0][2].replace('!','I').replace('|','I')
                        house = re.findall(house_pattern,text)[0][1]
                        age = int(re.findall(age_pattern,text)[0][1])
                        gender = re.findall(gender_pattern,text)[0][2][0]
                    except:
                        if lib == 'free':
                            text = detect_text_google(card_image)
                            return clean_data_write_csv(text,'paid')
                        else:
                            return False


                    if (age < 18) or (age >100) or (contains_special_characters(name)) or (contains_special_characters(spouse_name)) or (gender not in ['M','F']):
                        if lib == 'free':
                            text = detect_text_google(card_image)
                            return clean_data_write_csv(text,'paid')
                        else:
                            return False

                    row = [state,district,assembly[0][1].replace('!','I').replace('|','I'),part,vill_,wd_,po_,ps_,th_,pc_,section[0].replace('!','I').replace('|','I'),card_count,name,spouse,spouse_name,house,age,gender]
                    print(row,lib)
                    try:
                        with open(f'./data/{parts[-2]}.csv','a',newline='',encoding='utf-8') as f:
                            csv_writer = csv.writer(f)
                            csv_writer.writerow(row)
                        return True
                    except:
                        return False
                    
                text = detect_text_tesseract(card_image)
                try:
                    status = clean_data_write_csv(text,'free')
                except:
                    status = False
                if status == False:
                    if ('Gender' in text) and ('Number' in text) and ('Name' in text):
                        row = [state,district,assembly,part,card_count]
                    else:
                        row = [state,district,assembly,part,card_count,'DELETED']
                    try:
                        with open('./data/errors.csv','a',newline='',encoding='utf-8') as err:
                            csv_writer = csv.writer(err)
                            csv_writer.writerow(row)
                    except:
                        pass
                    
                    # if not os.path.exists(f'./data/error_cards/{state}/{district}/{assembly}/{part}'):
                    #     os.makedirs(f'./data/error_cards/{state}/{district}/{assembly}/{part}')
                    
                    # with open(f'./data/error_cards/{state}/{district}/{assembly}/{part}/{card_count}.txt','w') as w:
                    #     w.write(text)



with open('./data/output.csv','a',newline='',encoding='utf-8') as f:
    csv_writer = csv.writer(f)
    heading = ['State','District','Assembly','Part Detail','Main Town or Village','Ward','Post Office','Police Station','Tehsil','Pincode','Section','Card No.','Name','Spouse Relation','Spouse Name','House No.','Age','Gender']
    csv_writer.writerow(heading)


with open('./data/errors.csv','a',newline='',encoding='utf-8') as err:
    csv_writer = csv.writer(err)
    heading = ['State','District','Assembly','Part Detail','Card No.']
    csv_writer.writerow(heading)


src = './src'
for root,dirs,files in os.walk(src):
    for file in files:
        if file.endswith('.pdf'):
            if 'completed_files' not in root:
                pdf_path = os.path.join(root,file)
                o = main(pdf_path)
                if o != 0:
                    with open('./data/done.txt','a',encoding='utf-8') as f:
                        f.write(pdf_path+'\n')
