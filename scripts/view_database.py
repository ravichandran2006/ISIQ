import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "bis_standards.db")

def view_database(limit=10, search=None):
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Total counts
    cursor.execute("SELECT COUNT(*) FROM standards")
    total_stds = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM amendments")
    total_amds = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM standard_references")
    total_refs = cursor.fetchone()[0]

    print("=" * 70)
    print(f"  BISENSE DATABASE VIEWER: {os.path.abspath(DB_PATH)}")
    print("=" * 70)
    print(f"  • Total Standards Indexed: {total_stds}")
    print(f"  • Total Amendments:        {total_amds}")
    print(f"  • Normative References:    {total_refs}")
    print("-" * 70)

    # 2. Query standards
    if search:
        print(f"  [Searching for '{search}']\n")
        query = """
            SELECT id, standard_number, publication_year, reaffirmed_year, status, certification_scheme, title 
            FROM standards 
            WHERE standard_number LIKE ? OR title LIKE ?
            LIMIT ?
        """
        cursor.execute(query, (f"%{search}%", f"%{search}%", limit))
    else:
        print(f"  [Top {limit} Standards in Database]\n")
        query = """
            SELECT id, standard_number, publication_year, reaffirmed_year, status, certification_scheme, title 
            FROM standards 
            ORDER BY id ASC 
            LIMIT ?
        """
        cursor.execute(query, (limit,))

    rows = cursor.fetchall()
    for row in rows:
        std_id, num, pub_yr, reaff_yr, status, scheme, title = row
        print(f"  ID: {std_id:<4} | {num:<12} (Pub: {pub_yr or 'N/A'}, Reaff: {reaff_yr or 'N/A'})")
        print(f"  Title:  {title}")
        print(f"  Status: {status} | Scheme: {scheme}")

        # Show amendments for this standard
        cursor.execute("SELECT amendment_number, amendment_year, status FROM amendments WHERE standard_id = ?", (std_id,))
        amds = cursor.fetchall()
        if amds:
            amd_strs = [f"{a[0]} ({a[1] or 'Active'})" for a in amds]
            print(f"  Amendments: {', '.join(amd_strs)}")
        print("  " + "-" * 66)

    conn.close()

if __name__ == "__main__":
    search_term = sys.argv[1] if len(sys.argv) > 1 else None
    view_database(limit=10, search=search_term)
