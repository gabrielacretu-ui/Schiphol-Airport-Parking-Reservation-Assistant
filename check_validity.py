from functions.FUNCTIONS_SANITIZE_input import check_plate

lista=['6XTN50','6XTN59','XTN47','6XTN47','47RGBL','1ZKJ05','6XTN75','VR295H','6XTN75','1ZKJ05','47RGBL','6XTN47','XTN47','6XTN59','6XTN50','6XTN67','HBR74J','6XTN43','47SKLP','6XTN45']
for l in lista:
          plate = l.strip()  # remove newline characters
          result = check_plate(plate)
          if result["status"] == "success":
              print(f"{l} is T")


