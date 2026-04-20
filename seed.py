import json
import uuid6
from db_setup import SessionLocal, Profile

def clear_database():
    """Delete all profiles from the database"""
    db = SessionLocal()
    try:
        deleted_count = db.query(Profile).delete()
        db.commit()
        print(f"✓ Cleared {deleted_count} profiles from the database.")
    except Exception as e:
        print(f"✗ Error clearing database: {e}")
        db.rollback()
    finally:
        db.close()

def seed_data():
    """Seed database with profiles from JSON file"""
    db = SessionLocal()
    try:
        with open('seed_profiles.json', 'r', encoding='utf-8') as f:
            full_data = json.load(f)
        
        # Access the 'profiles' key from the JSON structure
        profiles_list = full_data.get("profiles", [])
        
        print(f"✓ Found {len(profiles_list)} profiles in the JSON file.")

        if not profiles_list:
            print("✗ No profiles found inside the 'profiles' key!")
            return

        # Get all existing names in one query for idempotency
        existing_names = {name for (name,) in db.query(Profile.name).all()}
        
        new_profiles = []
        added_count = 0
        skipped_count = 0
        
        for i, item in enumerate(profiles_list):
            # Convert name to lowercase for consistency
            name_lower = item.get('name', '').strip().lower()
            
            if name_lower and name_lower not in existing_names:
                new_profile = Profile(
                    id=str(uuid6.uuid7()),
                    name=name_lower,
                    gender=item.get('gender'),
                    gender_probability=float(item.get('gender_probability', 0)) if item.get('gender_probability') else None,
                    age=int(item.get('age')) if item.get('age') else None,
                    age_group=item.get('age_group'),
                    country_id=item.get('country_id'),
                    country_name=item.get('country_name'),
                    country_probability=float(item.get('country_probability', 0)) if item.get('country_probability') else None
                )
                new_profiles.append(new_profile)
                existing_names.add(name_lower)  # Update existing names to prevent duplicates in same batch
                added_count += 1
            else:
                skipped_count += 1
            
            # Print progress every 200 profiles
            if (i + 1) % 200 == 0:
                print(f"  Processing {i + 1}/{len(profiles_list)} profiles...")
        
        if new_profiles:
            # Batch insert for better performance
            db.add_all(new_profiles)
            db.commit()
            print(f"✓ Successfully added {added_count} new profiles to the database!")
        else:
            print("⚠ No new profiles to add.")
        
        if skipped_count > 0:
            print(f"⚠ Skipped {skipped_count} profiles (already exist).")
        
        print("✓ Database seeding complete!")
        
    except FileNotFoundError:
        print("✗ Error: seed_profiles.json file not found!")
    except Exception as e:
        print(f"✗ Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_database()
    seed_data()