import openai
import os
import requests
import uuid
import db
import json
from flask import Flask, request, jsonify, send_file, render_template,redirect,session
from flask_session import Session
from flask import flash
# Add your OpenAI API key
OPENAI_API_KEY = "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"
openai.api_key = OPENAI_API_KEY

# Add your ElevenLabs API key
ELEVENLABS_API_KEY = "d33d4fbd45a22dad18a96455a3f3737c"
ELEVENLABS_VOICE_STABILITY = 0.30
ELEVENLABS_VOICE_SIMILARITY = 0.75

# Choose your favorite ElevenLabs voice
ELEVENLABS_VOICE_NAME = "Hugh"
ELEVENLABS_ALL_VOICES = []

app = Flask(__name__)
app.config['SECRET_KEY'] = '43a383d720e93f7ecf63de094ff021a5'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def get_voices() -> list:
    """Fetch the list of available ElevenLabs voices.

    :returns: A list of voice JSON dictionaries.
    :rtype: list

    """
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY
    }
    response = requests.get(url, headers=headers)
    return response.json()["voices"]


def transcribe_audio(filename: str) -> str:
    """Transcribe audio to text.

    :param filename: The path to an audio file.
    :returns: The transcribed text of the file.
    :rtype: str

    """
    with open(filename, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript.text


def generate_reply(conversation: list) -> str:
    """Generate a ChatGPT response.

    :param conversation: A list of previous user and assistant messages.
    :returns: The ChatGPT response.
    :rtype: str

    """
    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=[
            {"role": "system", "content": "You are a helpful assistant."},
        ] + conversation
    )
    return response["choices"][0]["message"]["content"]


def generate_audio(text: str, output_path: str = "") -> str:
    """Converts

    :param text: The text to convert to audio.
    :type text : str
    :param output_path: The location to save the finished mp3 file.
    :type output_path: str
    :returns: The output path for the successfully saved file.
    :rtype: str

    """
    voices = ELEVENLABS_ALL_VOICES
    #print("inside audio 1")
    try:
        voice_id = next(filter(lambda v: v["name"] == ELEVENLABS_VOICE_NAME, voices))["voice_id"]
      #  print("inside audio 2")
    except StopIteration:
     #   print("inside audio 3")
        voice_id = voices[0]["voice_id"]
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "content-type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": ELEVENLABS_VOICE_STABILITY,
            "similarity_boost": ELEVENLABS_VOICE_SIMILARITY,
        }
    }
    #print("inside audio 4")
    response = requests.post(url, json=data, headers=headers)
   # print("inside audio 5")
    with open(output_path, "wb") as output:
        output.write(response.content)
        # print("inside audio 6")
    return output_path

@app.route('/', methods = ['GET', 'POST'])
def home():
    if session.get("email")!=None:
        return redirect("/chatbot")
    return render_template("signin.html")


@app.route('/signup', methods = ['GET', 'POST'])
def signup():
    return render_template("signup.html")



@app.route('/signin', methods = ['GET', 'POST'])
def signin():
  
    status, username ,email= db.check_user()
    if status==True:
         session["username"]=username
         session["email"] = email

    data = {
        "username": username,
        "email":email,
        "status": status
    }
    

    return json.dumps(data)



@app.route('/register', methods = ['GET', 'POST'])
def register():
    status = db.insert_data()
    return json.dumps(status)

@app.route("/logout", methods = ['GET', 'POST'])
def logout():
    session["username"] = None
    session["email"] = None
    return redirect('/')

@app.route("/profile", methods = ['GET', 'POST'])
def profile():
    
    return render_template('profile.html',username=session.get("username"),email=session.get("email"))

@app.route("/history", methods = ['GET', 'POST'])
def history():  
    conversation=db.history_retrive(username=session.get("username"),email=session.get("email"))
    return render_template('history.html',conversation=conversation)

@app.route("/changepassword", methods = ['GET', 'POST'])
def changepassword():
    
    status= db.updatepassword(session.get("username"),session.get("email"))
    print(session.get("username"),session.get("email"))
    data = {
        "status": status
    }

    return json.dumps(data)
    


@app.route('/chatbot', methods = ['GET', 'POST'])
def index():
    """Render the index page."""
    if session.get("email")==None:
        return redirect("/")
    return render_template('chatbot.html', username=session.get("username"))


@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Transcribe the given audio to text using Whisper."""
    if 'file' not in request.files:
        return 'No file found', 400
    file = request.files['file']
    recording_file = f"{uuid.uuid4()}.wav"
    recording_path = f"uploads/{recording_file}"
    os.makedirs(os.path.dirname(recording_path), exist_ok=True)
    file.save(recording_path)
    transcription = transcribe_audio(recording_path)
    return jsonify({'text': transcription})


@app.route('/ask', methods=['POST'])
def ask():
    """Generate a ChatGPT response from the given conversation, then convert it to audio using ElevenLabs."""
    conversation = request.get_json(force=True).get("conversation", "")
    reply = generate_reply(conversation)
    reply_file = f"{uuid.uuid4()}.mp3"
    reply_path = f"outputs/{reply_file}"
    os.makedirs(os.path.dirname(reply_path), exist_ok=True)
    generate_audio(reply, output_path=reply_path)
    # print(conversation[0]['content'])
    # print(reply)
    # print(username)
    db.history_insert(session.get("username"),conversation[0]['content'],reply,session.get("email"))
    return jsonify({'text': reply, 'audio': f"/listen/{reply_file}"})


@app.route('/listen/<filename>')
def listen(filename):
    """Return the audio file located at the given filename."""
    return send_file(f"outputs/{filename}", mimetype="audio/mp3", as_attachment=False)

@app.route('/feedback', methods=['GET'])
def feedback():
    return render_template('feedback.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    feedback_message = request.form.get('message')  # Get the feedback message from the form
    # Store the feedback in MongoDB
    feedback_data = {'message': feedback_message}
    print(request.files)
    if 'upload' in request.files:
        upload_file = request.files['upload']  # Get the uploaded file object
        filename = upload_file.filename
        if filename!='':
            # Save the uploaded file to a specific directory
            upload_dir = 'static/feedback'
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            file_path = os.path.join(upload_dir, filename)
            file_path = file_path.replace("\\", "/")
            upload_file.save(file_path)
            
            # Store the feedback message and image path in MongoDB
            feedback_data = {'message': feedback_message, 'image_path': file_path}

        print(feedback_data)
    status=db.feedback_insert(session.get('username'),session.get('email'),feedback_data)
    if status:
        flash('Feedback submitted successfully!', 'success')
    # Redirect to the /feedback page after successful submission
    else:
        flash('Failed!!!!', 'error')
    return redirect("/feedback")
@app.context_processor
def inject_functions():
    def message_category(message):
        if 'success' in message:
            return 'success'
        elif 'error' in message:
            return 'error'
        elif 'warning' in message:
            return 'warning'
        else:
            return ''
    return dict(message_category=message_category)



# admin 
@app.route('/admin',methods=['GET','POST'])
def admin():
    if session.get("admin")!=None:
        return redirect("/admin/dashboard")
    return render_template('admin_login.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    status=db.adminlogin()
    print(status,"nagaraja")
    if status:
        session['admin'] = True
        return redirect('/admin/dashboard')
    else:
        flash('Invalid credentials')
    return redirect('/admin')


@app.route('/admin/dashboard',methods=['GET','POST'])
def admin_dashboard():
    return render_template('admin_dashboard.html',data=db.admindata())

@app.route('/admin/feedback',methods=['GET','POST'])
def admin_feedback():
    return render_template('admin_feedback.html',feedbacks=db.fetch_feedback())

@app.route('/admin/manageUsers',methods=['GET','POST'])
def admin_manageUsers():
    return render_template('admin_manageusers.html',users=db.fetch_users())

@app.route('/admin/updateUser',methods=['GET','POST'])
def admin_updateuser():
    db.update_user()
    return redirect('/admin/manageUsers')


@app.route('/admin/conversation',methods=['GET','POST'])
def admin_conversation():
    email_counts = db.count_documents_by_email()
    print(email_counts)
    # for email, count in email_counts.items():
    #     print(f"Number of documents for email {email}: {count}")
    users=db.fetch_users()
    # for user in users:
    #     if user['email'] in email_counts:
    #         #print(user["email"],email_counts[user["email"]])
    #         user['count']=email_counts[user["email"]]
    #         print(user)

    return render_template('admin_conversation.html',users=users)



# @app.route('/admin/get_conversation', methods=['GET','POST'])
# def get_conversation(email):
#     conversation,user = db.fetch_conversation(email)
#     return render_template('admin_getconversation.html', conversation=conversation, user=user)
@app.route('/admin/get_conversation', methods=['POST'])
def get_conversation():
    email = request.form.get('email')
    name = request.form.get('name')
    conversation = db.fetch_conversation(email)
    return render_template('admin_getconversation.html', conversations=conversation, user=name)

@app.route('/admin/deleteConversation',methods=['GET','POST'])
def admin_deleteConversation():
    db.delete_conversation()
    return redirect('/admin/conversation')

@app.route('/admin/logout')
def admin_logout():
    # Clear the admin session and redirect to the login page
    session.clear()
    return redirect('/admin')

if ELEVENLABS_API_KEY:
    if not ELEVENLABS_ALL_VOICES:
        ELEVENLABS_ALL_VOICES = get_voices()
    if not ELEVENLABS_VOICE_NAME:
        ELEVENLABS_VOICE_NAME = ELEVENLABS_ALL_VOICES[0]["name"]

if __name__ == '__main__':
    app.run()
