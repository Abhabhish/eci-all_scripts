from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
from google.cloud import vision
import base64
import csv
from selenium.common.exceptions import NoSuchElementException,ElementClickInterceptedException
from google.api_core.exceptions import ServiceUnavailable
import requests




os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = './gcp_key.json'

def detect_text_google(path):
    client = vision.ImageAnnotatorClient()
    with open(path, "rb") as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description.replace(' ', '').replace('\n', '').lower()

def detect_text_my_model(img_url):
    url = 'http://192.168.1.201:8000/get_prediction/'
    res = requests.post(url,{'img_url':img_url})
    return res.json()['prediction']


def some_function(x):
    if x == 0:
        return []
    result = [0]
    for i in range(x - 1):
        result.append(i)
    return result

def download_base64_image(url, path):
    base64_image = url.split(",")[1]
    image_data = base64.b64decode(base64_image)
    with open(path, "wb") as image_file:
        image_file.write(image_data)


tries = 0
def solve_captcha_and_download_pdf(driver, wait,download_icon):
    global tries
    try:
        img_el = driver.find_element(By.XPATH, "//img[contains(@alt, 'captcha')]")
        img_src = img_el.get_attribute("src")
        # download_base64_image(img_src, 'captcha.jpg')
        # captcha_code = detect_text_google('captcha.jpg')
        captcha_code = detect_text_my_model(img_src)
        input_field = driver.find_element(By.XPATH, "//input[contains(@name, 'captcha')]")
        input_field.clear()
        input_field.send_keys(captcha_code)

        driver.execute_script("arguments[0].scrollIntoView(true);", download_icon)
        wait.until(EC.element_to_be_clickable(download_icon))
        download_icon.click()
        time.sleep(0.05)
        
        wait.until(EC.invisibility_of_element((By.XPATH, "//span[contains(@class, 'spinner-border spinner-border-sm spinner_custom')]")))
        try:
            warning_message = driver.find_element(By.XPATH, "//div[contains(@class, 'alert_content')]//p[text()='Invalid Catpcha']")
            print('warning_msg: ',warning_message.text)
            try: 
               driver.find_element(By.XPATH, "//img[contains(@id, 'cross')]").click()
            except:
                time.sleep(0.2)
                solve_captcha_and_download_pdf(driver, wait,download_icon)
            time.sleep(0.2)
            solve_captcha_and_download_pdf(driver, wait,download_icon)
        except NoSuchElementException:
            os.rename('captcha.jpg',captcha_code+'.jpg')
            time.sleep(0.2)

    except (IndexError, ServiceUnavailable):
        driver.find_element(By.XPATH, "//img[contains(@alt, 'refresh')]").click()
        time.sleep(3)
        solve_captcha_and_download_pdf(driver, wait,download_icon)

    except ElementClickInterceptedException:
        if tries < 3:
            driver.find_element(By.XPATH, "//img[contains(@alt, 'refresh')]").click()
            time.sleep(3)
            solve_captcha_and_download_pdf(driver, wait,download_icon)
            tries += 1
    
    except Exception as e:
        print(e)


# 2024-EROLLGEN-S20-59-FinalRoll-Revision1-HIN-3-WI.pdf
def done_files(src):
    rest = {}

    # for root,dirs,files in os.walk(src):
    #     for file in files:
    #         assembly = file.split('-')[3]
    #         srno = file.split('-')[7]
    #         if assembly not in rest:
    #             rest[assembly] = []
    #         rest[assembly].append(srno)
    # return rest

    with open('downloaded.txt','r') as dow:
        for line in dow:
            stripped_line = line.strip()
            assembly = stripped_line.split('-')[-6]
            srno = stripped_line.split('-')[-2]
            if assembly not in rest:
                rest[assembly] = []
            rest[assembly].append(srno)
    return rest


rest = done_files(r'smb://wdmycloudex4100.local/tech%20team/Abhishek/pdf%20backup/Andhra%20Pradesh-completed')


def main():
    # try:
        options = Options()
        options.add_argument('--no-sandbox')  # Bypass OS security model
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36')
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_window_size(1920, 1080)
        wait = WebDriverWait(driver, 100)

        driver.get('https://voters.eci.gov.in/download-eroll')
        time.sleep(5)

        state_dropdown = Select(driver.find_element(By.NAME, "stateCode"))

        for state in state_dropdown.options[2:3]: #1
            state.click()
            time.sleep(1)
            wait.until(EC.invisibility_of_element((By.XPATH, "//span[contains(@class, 'spinner-border spinner-border-sm spinner_custom')]")))
            # time.sleep(3)
            
            district_dropdown = Select(driver.find_element(By.NAME, "district"))
            for district in district_dropdown.options[1:]: #2
                district.click()
                time.sleep(1)
                wait.until(EC.invisibility_of_element((By.XPATH, "//span[contains(@class, 'spinner-border spinner-border-sm spinner_custom')]")))
                # time.sleep(3)

                assembly_dropdown = driver.find_element(By.XPATH, "//div[contains(@class, ' css-19bb58m')]")
                assembly_dropdown.click()
                time.sleep(1)
                assembly_options = len(driver.find_elements(By.XPATH, "//div[contains(@class, ' css-10wo9uf-option')]"))
                li = some_function(assembly_options)
                # li = [3] #3
                for i in li:
                    assembly = driver.find_elements(By.XPATH, "//div[contains(@class, ' css-10wo9uf-option')]")[i].text
                    def click_assembly():
                        try:
                            option = driver.find_elements(By.XPATH, "//div[contains(@class, ' css-10wo9uf-option')]")[i]
                            # print('state: ', state.text, 'district: ', district.text, 'assembly: ', option.text)
                            option.click()
                            time.sleep(1)
                            wait.until(EC.invisibility_of_element((By.XPATH, "//span[contains(@class, 'spinner-border spinner-border-sm spinner_custom')]")))
                            # time.sleep(3)
                        except IndexError:
                            assembly_dropdown = driver.find_element(By.XPATH, "//div[contains(@class, ' css-19bb58m')]")
                            assembly_dropdown.click()
                            time.sleep(1)
                            click_assembly()
                    click_assembly()

                    pdf_count = driver.find_element(By.XPATH, "//div[contains(@class, 'col-md text-right mr-2')]")
                    summary_row = [state.text, district.text, assembly,pdf_count.text]
                    with open('summary.csv','a') as summ:
                        csv_writer = csv.writer(summ)
                        csv_writer.writerow(summary_row)

                    # if assembly == '79 - Jalalabad': #4
                    #     print('JJJ')
                    #     assembly_dropdown.click()
                    #     continue

                    def download_current_page_pdfs():
                        table_body = driver.find_element(By.XPATH, "//tbody[@role='rowgroup']")
                        rows = table_body.find_elements(By.XPATH, ".//tr[@role='row']")
                        print('rows: ',len(rows))
                        for row in rows:
                          try:
                            cells = row.find_elements(By.XPATH, ".//td[@role='cell']")
                            print('cells: ',len(cells))
                            first_cell_text = cells[0].text
                            

                            # rest = {
                            #     # '26':['118','155'],
                            #     # '27':['11','118','139'],
                            #     # '28':['61','81','93'],
                            #     # '57':['146','154','170','182','183'],
                            #     # '58':['16','19','183'],
                            #     # '59':['54','55','67','105'],
                            #     # '60':[str(i) for i in range(1000)],
                            #     # '61':[str(i) for i in range(1000)],
                            #     # '62':[str(i) for i in range(1000)],
                            #     # '63':[str(i) for i in range(1000)],
                            #     # '64':[str(i) for i in range(1000)],
                            #     # '65':[str(i) for i in range(1000)],
                            #     '66':[str(i) for i in range(1000)],
                            #     '67':[str(i) for i in range(1000)],
                            #     '68':[str(i) for i in range(1000)],
                            #     '69':[str(i) for i in range(1000)],
                            #     '70':[str(i) for i in range(1000)]
                            # }

                            # if assembly.split(' ')[0] not in rest:
                            #     continue

                            # if first_cell_text.split(' ')[0] not in rest[assembly.split(' ')[0]]: # 6
                            #     continue

                            # skip pdf 
                            if assembly.split(' ')[0] in rest:
                                if first_cell_text.split(' ')[0] in rest[assembly.split(' ')[0]]:
                                    continue



                            download_icons = cells[1].find_elements(By.XPATH, ".//img[contains(@alt, 'download icon')]")
                            print('download icons: ',len(download_icons))
                            download_icon = download_icons[0]
                            solve_captcha_and_download_pdf(driver, wait, download_icon)
                            with open('main.csv', 'a', newline='') as ff:
                                csv_writer = csv.writer(ff)
                                csv_writer.writerow([state.text, district.text, assembly, first_cell_text])
                          except:
                              pass

                    while True:
                        page_num = driver.find_element(By.XPATH, "//span[contains(@class, 'm-2 control-btn2')]")
                        print(page_num.text)
                        next_btn = driver.find_elements(By.XPATH, "//button[contains(@class, 'control-btn')]")[2]
                        if page_num.text not in []:  # 5
                            download_current_page_pdfs()
                        if ('disabled' in next_btn.get_attribute('outerHTML')):
                            break
                        next_btn.click()
                    

                    assembly_dropdown.click()
        driver.quit()
if __name__ == "__main__":
    main()

