from app.core.config import Config

broker_url = Config.REDIS_URL
result_backend = Config.REDIS_URL
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True
task_track_started = True
task_time_limit = 1800  # 30 minutes