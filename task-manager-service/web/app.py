import os
import pika
import json
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    done = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(10), nullable=True)

    __table_args__ = (
        CheckConstraint("priority IN ('ALTA','MEDIA','BAJA') OR priority IS NULL", name='priority_check'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'done': self.done,
            'priority': self.priority
        }

RABBITMQ_URL = os.environ.get('RABBITMQ_URL')
def publish_message(queue_name, message):
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()

        channel.exchange_declare(exchange='dlx', exchange_type='direct', durable=True)
        channel.queue_declare(queue='tasks_failed', durable=True)
        channel.queue_bind(exchange='dlx', queue='tasks_failed', routing_key=queue_name)

        args = {'x-dead-letter-exchange': 'dlx'}
        channel.queue_declare(queue=queue_name, durable=True, arguments=args)

        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2) # make message persistent
        )
        connection.close()
        print(f" [x] Sent message to queue '{queue_name}'", flush=True)
    except Exception as e:
        print(f"Error publishing message: {e}", flush=True)

@app.route('/tasks', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()
    return jsonify({'tasks': [task.to_dict() for task in tasks]})

@app.route('/tasks', methods=['POST'])
def create_task():
    if not request.json or not 'title' in request.json:
        return jsonify({'error': 'Bad request: title is required'}), 400

    allowed_priorities = {None, 'ALTA', 'MEDIA', 'BAJA'}
    priority = request.json.get('priority') if request.json is not None else None
    if priority not in allowed_priorities:
        return jsonify({'error': "Invalid priority: must be 'ALTA', 'MEDIA' or 'BAJA' (or null)"}), 400

    new_task = Task(
        title=request.json['title'],
        description=request.json.get('description', ""),
        priority=priority
    )
    db.session.add(new_task)
    db.session.commit()

    publish_message('task_created', new_task.to_dict())

    return jsonify({'task': new_task.to_dict()}), 201

@app.route('/tasks/test-malformed', methods=['POST'])
def create_malformed_task():
    message = {'description': 'This is a bad task with no title', 'id': 999}
    publish_message('task_created', message)
    return jsonify({'status': 'Malformed message sent'}), 200

@app.route('/tasks/<int:task_id>/complete', methods=['PUT'])
def complete_task(task_id):
    task = Task.query.get(task_id)
    if task is None:
        return jsonify({'error': 'Task not found'}), 404
    
    task.done = True
    db.session.commit()
    
    publish_message('task_completed', task.to_dict())
    
    return jsonify({'task': task.to_dict()}), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
