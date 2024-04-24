const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const sqlite3 = require('sqlite3').verbose();
const cookieParser = require('cookie-parser');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');
const app = express();
const cors = require('cors');

// Middleware to parse JSON and handle cookies
app.use(express.json());
app.use(express.static(path.join(__dirname, '..', 'public')));

app.use(cookieParser());
app.use(express.urlencoded({ extended: true }));  // For parsing application/x-www-form-urlencoded
app.use(cors());

console.log(__dirname);

// Secret key for JWT (should be stored securely in a real-world scenario)
const SECRET_KEY = 'your_secret_jwt_key';

// Database setup
const db = new sqlite3.Database('./database.db', sqlite3.OPEN_READWRITE | sqlite3.OPEN_CREATE, (err) => {
    if (err) {
        console.error('Error opening database:', err.message);
    } else {
        console.log('Connected to the SQLite database.');
        createTables();
    }
});

// Create database tables
function createTables() {
    db.serialize(() => {
        db.run(`
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            userName TEXT UNIQUE,
            age INTEGER,
            gender TEXT,
            totalTrainTime INTEGER,
            totalEntries INTEGER,
            avgAnswers INTEGER
        )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS authentication (
            userId TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT,
            token TEXT,
            expiredTime DATE,
            role TEXT DEFAULT 'user',
            FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
        )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS answers (
            answerId INTEGER PRIMARY KEY AUTOINCREMENT,
            userId TEXT,
            date TEXT,
            photoName TEXT,
            classification TEXT,
            successAnswer INTEGER CHECK(successAnswer IN (0, 1, 2)),
            answerTime INTEGER,
            answerChange INTEGER,
            FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
        )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS exam (
            examId INTEGER PRIMARY KEY AUTOINCREMENT,
            userId TEXT,
            date TEXT,
            title TEXT,
            score INTEGER,
            totalExamTime INTEGER,
            FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
        )`);
    });
}

// Registration endpoint
app.post('/register', async (req, res) => {
    const {userName, password, email, age, gender} = req.body;
    if (!userName || !password || !email || !age || !gender) {
        return res.status(400).send('All fields are required');
    }
    const hashedPassword = await bcrypt.hash(password, 10);
    const userId = uuidv4();

    db.run('INSERT INTO users (id, userName, age, gender) VALUES (?, ?, ?, ?)', [userId, userName, age, gender], (err) => {
        if (err) {
            return res.status(500).send('Error registering new user in Users table: ' + err.message);
        }
        db.run('INSERT INTO authentication (userId, email, password, role) VALUES (?, ?, ?, "user")', [userId, email, hashedPassword], (authErr) => {
            if (authErr) {
                return res.status(500).send('Error registering new user in Authentication table: ' + authErr.message);
            }
            res.status(200).send('User registered successfully');
        });
    });
});

// Login endpoint
app.post('/login', (req, res) => {
    const {email, password} = req.body;
    const sql = `SELECT userId, password, role FROM authentication WHERE email = ?`;

    db.get(sql, [email], async (err, user) => {
        if (err) {
            console.error('Database error:', err.message);
            return res.status(500).send('Error on server side: ' + err.message);
        }
        if (!user) {
            return res.status(404).send('User not found');
        }
        if (await bcrypt.compare(password, user.password)) {
            const token = jwt.sign({id: user.userId, role: user.role}, SECRET_KEY, {expiresIn: '1h'});
            res.cookie('token', token, {httpOnly: true, secure: true});
            res.send({message: 'Login successful', role: user.role});
        } else {
            res.status(401).send('Password incorrect');
        }
    });
});

// Endpoint for serving the dashboard based on user role
app.get('/dashboard', (req, res) => {
    const token = req.cookies.token;
    if (!token) return res.status(401).send('Access Denied');
    try {
        const decoded = jwt.verify(token, SECRET_KEY);
        const filePath = decoded.role === 'manager' ? 'managerDashboard.html' : 'userDashboard.html';
        res.sendFile(path.join(__dirname, 'public', filePath));
    } catch (err) {
        res.status(400).send('Invalid Token');
    }
});

// Static pages routing
app.get('/', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'index.html')));
app.get('/login', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'views', 'login.html')));
app.get('/register', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'views', 'register.html')));
app.get('/chooseModel', (req, res) =>
{
    if (req.cookies.token) {
        const decoded = jwt.verify(req.cookies.token, SECRET_KEY);
        if (decoded.role === 'admin') {
            return res.redirect('/chooseModelAdmin');
        }
    }

    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'chooseModel.html'))
});
app.get('/chooseModelAdmin', (req, res) => {
    const token = req.cookies.token;
    if (!token) return res.status(401).send('Access Denied');
    const decoded = jwt.verify(token, SECRET_KEY);
    if (decoded.role !== 'admin') {
        return res.status(403).send('You do not have permission to access this page');
    } else {
        res.sendFile(path.join(__dirname, '..', 'public', 'views', 'chooseModelAdmin.html'));
    }
});

// Serve classified images for admin view
app.get('/classifiedImages', (req, res) => {
    const token = req.cookies.token;
    if (!token) return res.status(401).send('Access Denied');
    const decoded = jwt.verify(token, SECRET_KEY);
    if (decoded.role !== 'admin') {
        return res.status(403).send('You do not have permission to access this page');
    } else {
        res.sendFile(path.join(__dirname, '..', 'public', 'views', 'classifiedImagesAdmin.html'));
    }
});


// Handling form submission from chooseModel or chooseModelAdmin
app.post('/chooseModel', (req, res) => {
    const action = req.body.action;
    // Redirect or handle each action accordingly
    switch(action) {
        case 'classifiedImages':
            res.redirect('/classifiedImagesAdmin');
            break;
        case 'Train':
            res.send('Train functionality to be implemented');
            break;
        case 'FirstTest':
            res.send('First Test functionality to be implemented');
            break;
        case 'LastTest':
            res.send('Last Test functionality to be implemented');
            break;
        default:
            res.status(404).send('Action not found');
    }
});

// Serve the classifiedImagesAdmin.html
app.get('/classifiedImagesAdmin', (req, res) => {
    res.sendFile(path.join(__dirname,'..', 'public', 'views', 'classifiedImagesAdmin.html'));
});

// API to handle image classification from classifiedImagesAdmin.html
app.post('/classify-image', (req, res) => {
    const { fileName, category } = req.body;
    // Implement image classification and file handling logic
    console.log(`Classifying image ${fileName} as ${category}`);
    res.send(`Image ${fileName} classified as ${category}`);
});

// Assuming your images are stored in 'public/img/bankPhotos'
app.get('/random-image', (req, res) => {
    const imagesDir = path.join(__dirname, '..', 'public', 'img', 'bankPhotos');
    fs.readdir(imagesDir, (err, files) => {
        if (err) {
            return res.status(500).send('Failed to load images');
        }
        if (files.length === 0) {
            return res.status(404).send('No images found');
        }
        const randomIndex = Math.floor(Math.random() * files.length);
        const imagePath = files[randomIndex];
        res.json({ imagePath: `../img/bankPhotos/${imagePath}` });
    });
});


const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));