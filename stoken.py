from itsdangerous import URLSafeTimedSerializer
secret_key="Serializer234"
def entoken(data):
    serializer=URLSafeTimedSerializer(secret_key)
    return serializer.dumps(data,salt="extradata")
def dntoken(data):
    serializer=URLSafeTimedSerializer(secret_key)
    return serializer.loads(data,salt="extradata",max_age=180)