import os
import pika
import time
import sys

def main():
    rabbitmq_url = os.environ.get('RABBITMQ_URL')
    connection = None

    while not connection:
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            print("ErrorHandler: Conectado a RabbitMQ.", flush=True)
        except pika.exceptions.AMQPConnectionError:
            print("ErrorHandler: Esperando a RabbitMQ...", flush=True)
            time.sleep(5)

    channel = connection.channel()
    channel.queue_declare(queue='tasks_failed', durable=True)

    def callback(ch, method, properties, body):
        print(f" [x] Error recibido: {body}", flush=True)
        # Loguear a fichero
        with open("/app/error_log.txt", "a") as f:
            f.write(f"{time.ctime()}: {body.decode()}\n")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue='tasks_failed', on_message_callback=callback)

    print(' [*] ErrorHandler esperando mensajes fallidos.', flush=True)
    channel.start_consuming()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
