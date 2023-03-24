## Deployment

It is recommended to deploy on Linux (Ubuntu >= 20.04) with **nginx** and **gunicorn**.
Recommended setup includes **PostgreSQL** as database, and **Redis** as cache, 
cross-process locking mechanism and pub-sub server.

Sample config for nginx, as well as sample systemd service for gunicorn, are provided.

