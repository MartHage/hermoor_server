import json

from pyfcm import FCMNotification
from selenium import webdriver
import firebase_admin
from firebase_admin import credentials, firestore
import time

json_data = open("./personal_data.json").read()

data = json.loads(json_data)

osiris_username = data["osiris_username"]
osiris_password = data["osiris_password"]
api_key = data["api_key"]
registration_id = data["registration_id"]


def send_message(row):
    push_service = FCMNotification(api_key=api_key)

    if row[4] == "NRM":
        title = "Oei, je hebt een " + row[4]
    elif float(row[4]) >= 5:
        title = "Nice, je hebt een " + row[4] + " voor \"" + row[0] + "\""
    else:
        title = "Oei, je hebt een " + row[4] + " voor \"" + row[0] + "\""

    if row[3] == "":
        row[3] = "100"

    if row[2] == "":
        row[2] = "undefined"

    body = "Deze telt " + row[3] + "% mee, voor: \"" + row[1] + "\""

    message_title = title
    message_body = body
    print('hoi')
    push_service.notify_single_device(registration_id=registration_id, message_title=message_title, message_body=message_body)
    time.sleep(0.5)


def gather_data():
    # load website and login
    driver = webdriver.Chrome()
    driver.get('https://osiris.tue.nl/osiris_student_tueprd/ToonResultaten.do')

    time.sleep(0.1)
    username = driver.find_element_by_id("userNameInput")
    password = driver.find_element_by_id("passwordInput")

    username.send_keys(osiris_username)
    password.send_keys(osiris_password)

    submit = driver.find_element_by_id("submitButton")
    submit.click()

    time.sleep(0.1)
    table = driver.find_element_by_class_name("OraTableContent").find_elements_by_tag_name("tr")

    parsed_table = parse_table(table[1:])

    driver.close()
    return parsed_table


def parse_table(table):
    parsed_table = []

    for row in table:
        parsed_table.append([])

        cells = row.find_elements_by_tag_name("td")

        # course code; i = 0
        parsed_table[-1].append(parse_cell(cells[1].find_elements_by_tag_name("span")))
        # course name; i = 1
        parsed_table[-1].append(parse_cell(cells[2].find_elements_by_tag_name("span")))
        # description; i = 2
        parsed_table[-1].append(parse_cell(cells[3].find_elements_by_tag_name("span")))
        # test weight; i = 3
        parsed_table[-1].append(parse_cell(cells[5].find_elements_by_tag_name("span")))
        # result;      i = 4
        parsed_table[-1].append(parse_cell(cells[7].find_elements_by_tag_name("span")))
        # date;        i = 5
        parsed_table[-1].append(parse_cell(cells[9].find_elements_by_tag_name("span")))

    return parsed_table


def parse_cell(cell):
    if cell:
        return cell[0].get_attribute("innerText")
    else:
        return ""


def check_and_upload_data(table):
    cred = credentials.Certificate("./hermoor-ee0c4-firebase-adminsdk-ilytw-99fa1a0077.json")
    firebase_admin.initialize_app(cred)

    db = firestore.client()
    docs = db.collection(u'Grades')

    courses_old = [doc.id for doc in docs.get()]

    for row in table:
        course = db.collection(u'Grades').document(u'{course_code}'.format(course_code=row[0]))
        if row[0] not in courses_old:
            course.set({
                'course_name': row[1],
                '0': {
                    'description': row[2],
                    'weight': row[3],
                    'result': row[4],
                    'date': row[5]
                 }
            })
            courses_old.append(row[0])
            print("doei")
            send_message(row.copy())
        else:
            course_dict = course.get().to_dict()

            is_new_entry = True
            for i_str in [str(i) for i in range(len(course_dict)-1)]:

                is_same = True
                for index, attribute in enumerate(['description', 'weight', 'result', 'date']):
                    if course_dict[i_str][attribute] != row[index + 2]:
                        print(course_dict[i_str])
                        print(row)
                        print(course_dict[i_str][attribute])
                        print(row[index + 2])
                        print()
                        is_same = False
                        break

                if is_same:
                    is_new_entry = False
                    break

            if is_new_entry:
                print("boi")
                send_message(row.copy())
                course.update({
                    str(len(course_dict) - 1): {
                        'description': row[2],
                        'weight': row[3],
                        'result': row[4],
                        'date': row[5]
                    }
                })


check_and_upload_data(gather_data())
