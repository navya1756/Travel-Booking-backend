import smtplib
from email.message import EmailMessage
def send_mail(to,subject,body):
    try:
        server=smtplib.SMTP_SSL('smtp.gmail.com',465)
        server.login('sree.m.navya2003@gmail.com','eblt ofge phgo aowp')
        msg=EmailMessage()
        msg['FROM']='sree.m.navya2003@gmail.com'
        msg['TO']=to
        msg['SUBJECT']=subject
        msg.set_content(body)
        server.send_message(msg)
    except Exception as e:
        print(e)
        print('Email error')
    finally:
        if 'server' in locals():
            server.close()

