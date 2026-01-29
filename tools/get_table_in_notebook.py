import json


def _format_markdown_cell(value):
    if value is None:
        return "NULL"
    if isinstance(value, (list, dict)):
        rendered = json.dumps(value, ensure_ascii=True)
    else:
        rendered = str(value)
    rendered = rendered.replace("\r\n", "\n").replace("\r", "\n")
    multiline = "\n" in rendered
    if multiline:
        rendered = rendered.replace("\n", "<br>")
        rendered = f"\"{rendered}\""
    return rendered.replace("|", "\\|")


def export_table_to_markdown(database_name, table_name, output_file):
    """
    Export entire Spark SQL table to markdown format.
    
    Args:
        database_name: Name of the database
        table_name: Name of the table to export
        output_file: Path to output markdown file
    """
    spark = get_spark_session()
    
    # Read the entire table
    df = spark.table(f"{database_name}.{table_name}")
    
    with open(output_file, 'w') as f:
        f.write(f"# Table: {database_name}.{table_name}\n\n")
        
        # Get table comment if exists
        try:
            table_details = spark.sql(f"DESCRIBE EXTENDED {database_name}.{table_name}").collect()
            for detail in table_details:
                if detail.col_name == "Comment" and detail.data_type:
                    f.write(f"**Description:** {detail.data_type}\n\n")
                    break
        except:
            pass
        
        # Write schema information
        f.write("## Schema\n\n")
        f.write("| Column Name | Data Type | Nullable |\n")
        f.write("|-------------|-----------|----------|\n")
        
        for field in df.schema.fields:
            nullable = "Yes" if field.nullable else "No"
            f.write(f"| {field.name} | {field.dataType.simpleString()} | {nullable} |\n")
        
        f.write("\n")
        
        # Get row count
        row_count = df.count()
        f.write(f"**Total Rows:** {row_count}\n\n")
        
        # Write all data
        f.write("## Data\n\n")
        
        if row_count > 0:
            columns = df.columns
            
            # Create header
            f.write("| " + " | ".join(columns) + " |\n")
            f.write("|" + "|".join(["---" for _ in columns]) + "|\n")
            
            # Write all rows
            rows = df.collect()
            for row in rows:
                row_values = [_format_markdown_cell(row[col]) for col in columns]
                f.write("| " + " | ".join(row_values) + " |\n")
        else:
            f.write("*Table is empty*\n")
    
    print(f"Table exported to {output_file}")
    print(f"Total rows exported: {row_count}")


# Usage:
export_table_to_markdown(
    database_name="enigma_coral",
    table_name="sdt_protocol",
    output_file="sdt_protocol_table.md"
)
