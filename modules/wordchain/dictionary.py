from marisa_trie import Trie
import logging

logger: logging.Logger = logging.getLogger(__name__)

class IllegalWordException(Exception):
    def __init__(self, *args, **kwargs):
        return super().__init__("Từ nhập vào không hợp lệ", *args, **kwargs)

# For Testing
class SpecialWordException(Exception):
    def __init__(self, *args, **kwargs):
        return super().__init__("Kết quả bạn nhập vào có chứa kí tự đặc biệt", *args, **kwargs)
        

def reform_word(word: str) -> str:
    if word.__len__() < 3: raise IllegalWordException()
    word = word.strip().lower()
    if not word.isalpha(): raise IllegalWordException()
    return word

def check_input(msg_content: str):
    special_characters = (
        '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '_', '=', '+',
        '{', '}', '[', ']', '|', '\\', ';', ':', "'", '"', '<', '>', ',', '.', '/',
        '?', '~', '`'
    )
    vietnamese_characters: list = [
        'ă', 'â', 'đ', 'ê', 'ô', 'ơ', 'ư',
        'à', 'á', 'ả', 'ã', 'ạ', 'ằ', 'ắ', 'ẳ', 'ẵ', 'ặ',
        'ầ', 'ấ', 'ẩ', 'ẫ', 'ậ', 'è', 'é', 'ẻ', 'ẽ', 'ẹ',
        'ề', 'ế', 'ể', 'ễ', 'ệ', 'ì', 'í', 'ỉ', 'ĩ', 'ị',
        'ò', 'ó', 'ỏ', 'õ', 'ọ', 'ồ', 'ố', 'ổ', 'ỗ', 'ộ',
        'ờ', 'ớ', 'ở', 'ỡ', 'ợ', 'ù', 'ú', 'ủ', 'ũ', 'ụ',
        'ừ', 'ứ', 'ử', 'ữ', 'ự', 'ỳ', 'ý', 'ỷ', 'ỹ', 'ỵ'
    ]
    if " " in msg_content:
        return False
    if msg_content.startswith(special_characters):
        return False
    if msg_content.startswith("http"):
        return False
    for char in msg_content:
        for c in vietnamese_characters:
            if str(char) == str(c):
                return False
    return True


class Dictionary:
    __slots__ = "storage"
    
    def __init__(self):
        with open("modules/wordchain/wordlist.txt") as f:
            index = []
            for line in f.readlines():
                if line.strip().__len__() == 0: continue
                try: index.append(reform_word(line))
                except IllegalWordException: pass
                except Exception as e: logger.error(repr(e))
            self.storage = Trie(index)
            logger.info(f"Đã nạp {index.__len__()} từ vựng tiếng Anh vào bộ nhớ")
            
    def check(self, word: str):
        return reform_word(word) in self.storage
            
            
# For testing
if __name__ == "__main__":
    dictionary = Dictionary()
    while True:
        try:
            word = input("> ")
            ch = check_input(word)
            if not ch:
                raise SpecialWordException()
            else:
                print(dictionary.check(word))
        except Exception as e:
            print(repr(e))