import os
import pika
import json
import time
import requests

def send_email_notification(task_data):
    """Simula el envío de email usando webhook.site"""
    webhook_url = os.environ.get('WEBHOOK_URL', 'https://webhook.site/12345678-1234-1234-1234-123456789000')
    
    email_payload = {
        'task_id': task_data.get('id'),
        'title': task_data.get('title'),
        'description': task_data.get('description'),
        'status': 'completada',
        'message': f"La tarea '{task_data.get('title')}' ha sido completada."
    }
    
    try:
        response = requests.post(webhook_url, json=email_payload, timeout=5)
        print(f" [✓] Email enviado para tarea ID={task_data.get('id')} (Status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f" [✗] Error al enviar email para tarea ID={task_data.get('id')}: {str(e)}")

def main():
    rabbitmq_url = os.environ.get('RABBITMQ_URL')
    connection = None

    # Bucle para reintentar la conexión si RabbitMQ no está listo
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            print("Notifier: Conectado a RabbitMQ.")
        except pika.exceptions.AMQPConnectionError:
            print("Notifier: Esperando a RabbitMQ...")
            time.sleep(5)

    channel = connection.channel()
    channel.queue_declare(queue='task_completed', durable=True)

    def callback_task_completed(ch, method, properties, body):
        task_data = json.loads(body)
        print(f" [📧] Notificación recibida para tarea ID={task_data.get('id')}, Título='{task_data.get('title')}'")
        send_email_notification(task_data)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='task_completed', on_message_callback=callback_task_completed)

    print(' [*] Notifier esperando mensajes. Para salir presione CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    import sys
    try:
        main()
    except KeyboardInterrupt:
        print('Notifier interrumpido')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
