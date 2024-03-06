const express = require('express');
const bodyParser = require('body-parser');
const bcrypt = require('bcrypt');
const session = require('express-session');
const path = require('path');
const cors = require('cors');
const sqlite3 = require('sqlite3').verbose();

const app = express();

// Middleware configuration
app.use(cors());
app.use(session({
    secret: 'your_secret_key',
    resave: false,
    saveUninitialized: true,
    cookie: { secure: false, httpOnly: true }
}));
app.use(express.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '../public')));

// Database connection
const db = new sqlite3.Database(path.join(__dirname, '/ECG.db'), sqlite3.OPEN_READWRITE | sqlite3.OPEN_CREATE, (err) => {
    if (err) {
        console.error('Error opening database', err);
    } else {
        console.log('Connected to the ECG.db database.');
    }
});

// Function to create database tables
const createTables = () => {
    const userTable = `CREATE TABLE IF NOT EXISTS users (
        id TEXT UNIQUE PRIMARY KEY,
        userName TEXT,
        password TEXT NOT NULL,
        age INTEGER,
        AVG REAL,
        email TEXT UNIQUE,
        gender TEXT
    )`;

    const mainTable = `CREATE TABLE IF NOT EXISTS main (
        id TEXT,
        totalTrainTime INTEGER,
        totalEntries INTEGER,
        avg REAL,
        PRIMARY KEY (id),
        FOREIGN KEY (id) REFERENCES users (id) ON DELETE CASCADE
    )`;
    const answersTable = `CREATE TABLE IF NOT EXISTS answers (
            id INTEGER,
            date TEXT,
            photoName TEXT,
            classification TEXT,
            successAnswer INTEGER CHECK (successAnswer IN (0, 1, 2)),
            answerTime INTEGER,
            answerChange INTEGER,
            PRIMARY KEY (id, date),
            FOREIGN KEY (id) REFERENCES users (id) ON DELETE CASCADE
            )`;

    const examTable = `CREATE TABLE IF NOT EXISTS exam (
            id TEXT,
            date TEXT,
            title TEXT,
            score INTEGER,
            totalExamTime INTEGER,
            PRIMARY KEY (id, date),
            FOREIGN KEY (id) REFERENCES users (id) ON DELETE CASCADE
        )`

    // Add other table creation queries as needed

    db.run(userTable);
    db.run(mainTable);
    db.run(answersTable);
    db.run(examTable);
    // Execute other table creations here
};

// Call the function to ensure tables are created
createTables();

const checkAuthenticated = (req, res, next) => {
    if (req.session && req.session.userId) {
        // User is logged in, proceed to the next middleware
        next();
    } else {
        // User is not logged in, redirect to login page or send an error
        res.status(401).send('Unauthorized: No session available');
        // Or redirect: res.redirect('/login');
    }
};



app.get('/login', (req, res) => {
    res.sendFile(path.join(__dirname, '../public/views/login.html'));
});

app.get('/register', (req, res) => {
    res.sendFile(path.join(__dirname, '../public/views/register.html'));
});
app.get('/welcome',checkAuthenticated, (req, res) => {
    res.sendFile(path.join(__dirname, '../public/views/welcome.html'));
});
app.get('/chooseModel',checkAuthenticated, (req, res) => {
    res.sendFile(path.join(__dirname, '../public/views/chooseModel.html'));
});



// Registration endpoint
app.post('/register', async (req, res) => {
    const { userName, id, password, email, AVG, age,gender } = req.body;

    try {
        const hashedPassword = await bcrypt.hash(password, 10);
        const query = `INSERT INTO users (id, userName, password, email, AVG, age, gender) VALUES (?, ?, ?, ?, ?, ?, ?)`;

        db.run(query, [id, userName, hashedPassword, email, AVG, age, gender], function(err) {
            if (err) {
                res.status(500).json({ msg: 'Error registering new user', error: err });
            } else {
                req.session.userId = email; // Adjust according to your session management
                res.status(200).redirect('/welcome');
            }
        });
    } catch (error) {
        res.status(500).json({ msg: 'Server error', error });
    }
});

// Login endpoint
app.post('/login', async (req, res) => {
    const { id, password } = req.body;
    db.get(`SELECT * FROM users WHERE id = ?`, [id], async (err, user) => {
        if (err) {
            return res.status(500).json({ msg: 'Error logging in', error: err });
        }
        if (!user) {
            return res.status(404).json({ msg: 'User not found' });
        }
        const match = await bcrypt.compare(password, user.password);
        if (match) {
            req.session.userId = user.email; // Adjust according to your session management
            res.status(200).redirect('/welcome');

        } else {
            res.status(400).json({ msg: 'Incorrect password' });
        }
    });
});

app.post('/welcome', (req, res) => {
    res.redirect('/chooseModel');
});

app.post('/chooseModel', (req, res) => {
    chooseModel = req.body.chooseModel;
    if (chooseModel === "train") {
        res.redirect('/train');
    } else if (chooseModel === "firstExam") {
        res.redirect('/firstExam');
    } else if (chooseModel === "lastExam") {
        res.redirect('/lastExam');
    }
});

// Other endpoints as needed...

const PORT = 3000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server is running on port ${PORT}`);
});


// Optional: Clean up the database connection on server close
process.on('SIGINT', () => {
    db.close((err) => {
        if (err) {
            console.error(err.message);
        }
        console.log('Database connection closed.');
        process.exit(0);
    });
});
