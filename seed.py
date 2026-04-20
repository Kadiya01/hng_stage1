import json
import uuid6
from db_setup import SessionLocal, Profile

def clear_database():
    """Delete all profiles from the database"""
    db = SessionLocal()
    try:
        deleted_count = db.query(Profile).delete()
        db.commit()
        print(f" Cleared {deleted_count} profiles from the database.")
    except Exception as e:
        print(f" Error clearing database: {e}")
        db.rollback()
    finally:
        db.close()

def seed_data():
    db = SessionLocal()
    try:
        with open('seed_profiles.json', 'r') as f:
            full_data = json.load(f)
        
        # FIX: Access the 'profiles' key from your JSON structure
        profiles_list = full_data.get("profiles", [])
        
        print(f" Found {len(profiles_list)} profiles in the JSON file.")

        if not profiles_list:
            print(" No profiles found inside the 'profiles' key!")
            return

        # Get all existing names in one query
        existing_names = {name for (name,) in db.query(Profile.name).all()}
        
        new_profiles = []
        added_count = 0
        skipped_count = 0
        
        for i, item in enumerate(profiles_list):
            if item['name'] not in existing_names:
                new_profile = Profile(
                    id=str(uuid6.uuid7()),
                    name=item['name'],
                    gender=item.get('gender'),
                    gender_probability=item.get('gender_probability'),
                    age=item.get('age'),
                    age_group=item.get('age_group'),
                    country_id=item.get('country_id'),
                    country_name=item.get('country_name'),
                    country_probability=item.get('country_probability')
                )
                new_profiles.append(new_profile)
                added_count += 1
            else:
                skipped_count += 1
            
            # Print progress every 100 profiles
            if (i + 1) % 100 == 0:
                print(f" Processed {i + 1}/{len(profiles_list)} profiles...")
        
        if new_profiles:
            db.add_all(new_profiles)
            db.commit()
            print(f" Successfully added {added_count} new profiles to the database!")
        else:
            print(" No new profiles to add.")
        
        if skipped_count > 0:
            print(f" Skipped {skipped_count} profiles (already exist).")
        
        print(" Database seeding complete!")
        
    except Exception as e:
        print(f" Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_database()
    seed_data()