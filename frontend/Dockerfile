FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Start with the small official Nginx web-server image.
FROM nginx:alpine

# Remove Nginx's sample website, because we will use our own files.
RUN rm -rf /usr/share/nginx/html/*

# Copy our Nginx rulebook into its normal configuration location.
COPY nginx.conf /etc/nginx/nginx.conf

# Copy the HTML, CSS, and JavaScript files that Chrome will receive.
COPY public /usr/share/nginx/html

# Tell Docker that Nginx listens on door (port) 80 inside this container.
EXPOSE 80

# Start Nginx and keep it running in the foreground for Docker.
CMD ["nginx", "-g", "daemon off;"]
