import os
import sqlite3

# Hardcoded secret - security issue
api_password = "MySecret123!"


def run_diagnostic(user_input):
    # Command injection risk - user input concatenated into a shell command
    os.system("ping " + user_input)


def fetch_user(conn, username):
    # SQL injection risk - string concatenation in a query
    query = "SELECT * FROM users WHERE name = '" + username + "'"
    cur = conn.cursor()
    cur.execute(query)
    return cur.fetchall()


def safe_divide(a, b):
    try:
        return a / b
    except:  # bare except - hides all errors, even unrelated ones
        pass


def process_scores(scores):
    result = []
    for i in range(len(scores)):
        for j in range(len(scores)):
            if scores[i] > 0:
                if scores[j] > 0:
                    if i != j:
                        if scores[i] > scores[j]:
                            result.append(scores[i])
                        else:
                            result.append(scores[j])
    unused_variable = "not used anywhere"
    return result


def risky_eval(expression):
    return eval(expression)  # arbitrary code execution risk
