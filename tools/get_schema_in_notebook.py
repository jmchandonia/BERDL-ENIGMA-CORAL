from pyspark.sql import SparkSession
import json

def export_spark_database_schema(database_name, output_file, sample_rows=5):
    """
    Export complete Spark SQL database structure with comments and sample data.
    
    Args:
        database_name: Name of the database to export
        output_file: Path to output markdown file
        sample_rows: Number of sample rows to include per table
    """
    spark = get_spark_session()
    
    # Use the specified database
    spark.sql(f"USE {database_name}")
    
    # Get all tables in the database
    tables = spark.sql(f"SHOW TABLES IN {database_name}").collect()
    
    with open(output_file, 'w') as f:
        f.write(f"# Database Schema: {database_name}\n\n")
        f.write(f"Total Tables: {len(tables)}\n\n")
        f.write("---\n\n")
        
        for table_row in tables:
            table_name = table_row.tableName
            
            f.write(f"## Table: {table_name}\n\n")
            
            # Get table comment
            try:
                table_details = spark.sql(f"DESCRIBE EXTENDED {database_name}.{table_name}").collect()
                for detail in table_details:
                    if detail.col_name == "Comment" and detail.data_type:
                        f.write(f"**Table Description:** {detail.data_type}\n\n")
                        break
            except:
                pass
            
            # Get detailed schema with comments
            f.write("### Schema\n\n")
            f.write("| Column Name | Data Type | Nullable | Comment |\n")
            f.write("|-------------|-----------|----------|----------|\n")
            
            # Get schema with comments
            df = spark.table(f"{database_name}.{table_name}")
            schema_info = spark.sql(f"DESCRIBE {database_name}.{table_name}").collect()
            
            for field in schema_info:
                if field.col_name and not field.col_name.startswith('#'):
                    col_name = field.col_name
                    data_type = field.data_type
                    
                    # Get comment if exists
                    comment = ""
                    if len(field) > 2:
                        comment = field[2] if field[2] else ""
                    
                    # Check if nullable
                    nullable = "Yes"
                    for schema_field in df.schema.fields:
                        if schema_field.name == col_name:
                            nullable = "Yes" if schema_field.nullable else "No"
                            break
                    
                    f.write(f"| {col_name} | {data_type} | {nullable} | {comment} |\n")
            
            f.write("\n")
            
            # Get sample data
            f.write(f"### Sample Data ({sample_rows} rows)\n\n")
            
            try:
                sample_df = spark.table(f"{database_name}.{table_name}").limit(sample_rows)
                samples = sample_df.collect()
                
                if samples:
                    # Create header
                    columns = sample_df.columns
                    f.write("| " + " | ".join(columns) + " |\n")
                    f.write("|" + "|".join(["---" for _ in columns]) + "|\n")
                    
                    # Write sample rows
                    for row in samples:
                        row_values = [str(row[col]) if row[col] is not None else "NULL" for col in columns]
                        f.write("| " + " | ".join(row_values) + " |\n")
                else:
                    f.write("*Table is empty*\n")
            except Exception as e:
                f.write(f"*Error retrieving sample data: {str(e)}*\n")
            
            f.write("\n---\n\n")
    
    print(f"Schema exported to {output_file}")


def export_spark_database_schema_json(database_name, output_file, sample_rows=5):
    """
    Alternative: Export as JSON format for programmatic consumption.
    """
    spark = get_spark_session()
    spark.sql(f"USE {database_name}")
    
    tables = spark.sql(f"SHOW TABLES IN {database_name}").collect()
    
    database_schema = {
        "database_name": database_name,
        "total_tables": len(tables),
        "tables": []
    }
    
    for table_row in tables:
        table_name = table_row.tableName
        table_info = {
            "table_name": table_name,
            "comment": "",
            "columns": [],
            "sample_data": []
        }
        
        # Get table comment
        try:
            table_details = spark.sql(f"DESCRIBE EXTENDED {database_name}.{table_name}").collect()
            for detail in table_details:
                if detail.col_name == "Comment" and detail.data_type:
                    table_info["comment"] = detail.data_type
                    break
        except:
            pass
        
        # Get schema
        df = spark.table(f"{database_name}.{table_name}")
        schema_info = spark.sql(f"DESCRIBE {database_name}.{table_name}").collect()
        
        for field in schema_info:
            if field.col_name and not field.col_name.startswith('#'):
                col_info = {
                    "name": field.col_name,
                    "type": field.data_type,
                    "nullable": True,
                    "comment": field[2] if len(field) > 2 and field[2] else ""
                }
                
                for schema_field in df.schema.fields:
                    if schema_field.name == field.col_name:
                        col_info["nullable"] = schema_field.nullable
                        break
                
                table_info["columns"].append(col_info)
        
        # Get sample data
        try:
            sample_df = spark.table(f"{database_name}.{table_name}").limit(sample_rows)
            table_info["sample_data"] = [row.asDict() for row in sample_df.collect()]
        except:
            table_info["sample_data"] = []
        
        database_schema["tables"].append(table_info)
    
    with open(output_file, 'w') as f:
        json.dump(database_schema, f, indent=2, default=str)
    
    print(f"Schema exported to {output_file}")


# Usage:
if __name__ == "__main__":
    # Recommended: Export as Markdown (best for LLM consumption)
    export_spark_database_schema(
        database_name="enigma_coral",
        output_file="enigma_coral_schema.md",
        sample_rows=5
    )
    
    # Alternative: Export as JSON
    # export_spark_database_schema_json(
    #     database_name="enigma_coral",
    #     output_file="enigma_coral_schema.json",
    #     sample_rows=5
    # )
