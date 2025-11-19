# worker/worker.py
import os
import pika
import json
import time

def main():
    rabbitmq_url = os.environ.get('RABBITMQ_URL')
    connection = None

    # Bucle para reintentar la conexión si RabbitMQ no está listo
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            print("Worker: Conectado a RabbitMQ.")
        except pika.exceptions.AMQPConnectionError:
            print("Worker: Esperando a RabbitMQ...")
            time.sleep(5)

    channel = connection.channel()
    channel.queue_declare(queue='task_created', durable=True)

    def callback(ch, method, properties, body):
        task_data = json.loads(body)
        print(f" [x] Recibido y procesado nuevo task: ID={task_data.get('id')}, Título='{task_data.get('title')}'")
        # Aquí iría la lógica de procesamiento (enviar email, etc.)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='task_created', on_message_callback=callback)

    print(' [*] Esperando mensajes. Para salir presione CTRL+C')
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrumpido')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)