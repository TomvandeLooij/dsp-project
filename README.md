# Infrastructural effect of fires in Amsterdam
Prototype created in collaboration with the municipality of Amsterdam and the University of Amsterdam.

## Setting up the prototype locally
Create a new environment:

    python3 -m venv env

Activate environment:

    source env/bin/activate

Install depedencies:

    pip install -r requirements.txt

Run the server:

    # UNIX
    FLASK_APP=app.py FLASK_ENV=development flask run

    # Windows
    set FLAKS_APP=app.py
    set FLASK_ENV=development
    flask run
