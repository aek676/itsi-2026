# web/app.py
import os
import pika
import json
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# --- Configuración de la Base de Datos ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Modelo de la Base de Datos ---
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    done = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'done': self.done
        }

# --- Configuración de RabbitMQ ---
RABBITMQ_URL = os.environ.get('RABBITMQ_URL')
def publish_message(queue_name, message):
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)
        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2) # make message persistent
        )
        connection.close()
        print(f" [x] Sent message to queue '{queue_name}'")
    except Exception as e:
        print(f"Error publishing message: {e}")

# --- Endpoints de la API ---
@app.route('/tasks', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()
    return jsonify({'tasks': [task.to_dict() for task in tasks]})

@app.route('/tasks', methods=['POST'])
def create_task():
    if not request.json or not 'title' in request.json:
        return jsonify({'error': 'Bad request: title is required'}), 400

    new_task = Task(
        title=request.json['title'],
        description=request.json.get('description', "")
    )
    db.session.add(new_task)
    db.session.commit()

    # Publicar mensaje en RabbitMQ
    publish_message('task_created', new_task.to_dict())

    return jsonify({'task': new_task.to_dict()}), 201

@app.route('/tasks/<int:task_id>/complete', methods=['PUT'])
def complete_task(task_id):
    task = Task.query.get(task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    
    task.done = True
    db.session.commit()
    
    # Publicar mensaje en RabbitMQ
    publish_message('task_completed', task.to_dict())
    
    return jsonify({'task': task.to_dict()}), 200

#... (otros endpoints como get_task, delete_task pueden ser añadidos de forma similar)

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # Crea las tablas si no existen
    app.run(host='0.0.0.0', port=5000, debug=True)
