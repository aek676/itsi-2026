import os
import pika
import json
import time
import sys

def main():
    rabbitmq_url = os.environ.get('RABBITMQ_URL')
    connection = None

    while not connection:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            print("Worker: Conectado a RabbitMQ.", flush=True)
        except pika.exceptions.AMQPConnectionError:
            print("Worker: Esperando a RabbitMQ...", flush=True)
            time.sleep(5)

    channel = connection.channel()
    
    channel.exchange_declare(exchange='dlx', exchange_type='direct', durable=True)
    channel.queue_declare(queue='tasks_failed', durable=True)
    channel.queue_bind(exchange='dlx', queue='tasks_failed', routing_key='task_created')

    args = {'x-dead-letter-exchange': 'dlx'}
    channel.queue_declare(queue='task_created', durable=True, arguments=args)

    def callback(ch, method, properties, body):
        try:
            task_data = json.loads(body)
        except json.JSONDecodeError:
            print(f" [!] Mensaje no es JSON válido: {body}", flush=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        if 'title' not in task_data:
            print(f" [!] Mensaje malformado (sin title): {body}", flush=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        print(f" [x] Recibido y procesado nuevo task: ID={task_data.get('id')}, Título='{task_data.get('title')}'", flush=True)
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