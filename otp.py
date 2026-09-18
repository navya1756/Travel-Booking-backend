#g7vD9v
import random
def genotp():
    otp=''
    c_l=[chr(i) for i in range(ord('A'),ord('Z')+1)] # captial letters
    s_l=[chr(i) for i in range(ord('a'),ord('z')+1)]  #small letters
    for i in range(2):
        otp=otp+random.choice(c_l)+str(random.randint(0,9))+random.choice(s_l)
    return otp
