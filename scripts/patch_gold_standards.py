import sqlite3

def patch_gold():
    conn = sqlite3.connect("data/bis_standards.db")
    c = conn.cursor()
    c.execute("""
        UPDATE standards 
        SET domain = 'Precious Metals and Hallmarking' 
        WHERE standard_number LIKE '%1417%' 
           OR standard_number LIKE '%1418%' 
           OR standard_number LIKE '%17278%' 
           OR standard_number LIKE '%2790%' 
           OR standard_number LIKE '%2112%'
           OR standard_number LIKE '%639%'
    """)
    c.execute("""
        UPDATE standards 
        SET scope = 'This standard prescribes requirements for refined gold bars, gold bullion bars, gold biscuits, cast bars and minted bars for good delivery, specifying purity grades, fineness tolerances, dimensions, assaying, serial numbering, and marking.' 
        WHERE standard_number LIKE '%17278%'
    """)
    c.execute("""
        UPDATE standards 
        SET scope = 'This standard prescribes cupellation fire assay method for the determination of gold in gold bullion, gold bars, refined gold biscuits, gold alloys, and gold jewellery or artefacts.' 
        WHERE standard_number LIKE '%1418%'
    """)
    c.execute("""
        UPDATE standards 
        SET scope = 'This standard specifies requirements for fineness and marking of gold and gold alloys, gold bullion, jewellery, artefacts, and mandatory BIS Hallmarking with Hallmark Unique Identification (HUID).' 
        WHERE standard_number LIKE '%1417%'
    """)
    conn.commit()
    conn.close()
    print("Gold standards metadata successfully updated.")

if __name__ == "__main__":
    patch_gold()
