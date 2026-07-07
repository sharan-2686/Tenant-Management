from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker 
db_url="postgresql+psycopg://postgres.uyjugjeitqmccmgfzakd:rohitsharma45@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"
from supabase import create_client
SUPABASE_URL ="https://uyjugjeitqmccmgfzakd.supabase.co"
SUPABASE_KEY ="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV5anVnamVpdHFtY2NtZ2Z6YWtkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjE3NDk5NSwiZXhwIjoyMDk3NzUwOTk1fQ.FtanlHoAU1SocGE7YGCkyVuKAMQ_MQkb5yuYBoAf2NY"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
engine=create_engine(db_url, pool_pre_ping=True)
SessionLocal=sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(result.scalar())
        print("Database connected successfully!")
except Exception as e:
    print("Connection failed:", e)