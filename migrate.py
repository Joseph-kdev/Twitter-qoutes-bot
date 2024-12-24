import json
from datetime import datetime
from main import app, db, Quote

def migrate_json_to_sqlite():
    with app.app_context():
        try:
            # Read JSON files
            with open('./data/data.json', 'r') as f:
                quotes = json.load(f)
            
            with open('./data/tweeted.json', 'r') as f:
                tweeted = json.load(f)
            
            # Add quotes to database
            for quote_data in quotes:
                is_tweeted = any(
                    t.get('Quote') == quote_data.get('Quote') and 
                    t.get('Page') == quote_data.get('Page') 
                    for t in tweeted
                )
                
                quote = Quote(
                    text=quote_data['Quote'],
                    page=quote_data['Page'],
                    tweeted=is_tweeted,
                    tweeted_at=datetime.utcnow() if is_tweeted else None
                )
                db.session.add(quote)
            
            db.session.commit()
            print("Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            print(f"Error during migration: {str(e)}")

if __name__ == "__main__":
    migrate_json_to_sqlite()