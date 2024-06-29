const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const sqlite3 = require('sqlite3').verbose();
const cookieParser = require('cookie-parser');
const {v4: uuidv4} = require('uuid');
const path = require('path');
const fs = require('fs');
const app = express();
const cors = require('cors');
const verifyToken = require('./authMiddleware');
const config = require('../config/config');
const PORT = config.server.port || 3000;
const SECRET_KEY = config.secret_key.key;


// Middleware to parse JSON and handle cookies
app.use(express.json());
app.use(express.static(path.join(__dirname, '..', 'public')));
app.use(cookieParser());
app.use(express.urlencoded({extended: true}));
app.use(cors());

// Middleware to check token validity and refresh if needed
function checkToken(req, res, next) {
    const token = req.cookies.token;
    if (!token) return res.status(401).json({message: 'NoToken', redirect: '/login'});

    try {
        const decoded = jwt.verify(token, SECRET_KEY);
        const currentTime = Math.floor(Date.now() / 1000);
        const expirationTime = decoded.exp;
        const timeLeft = expirationTime - currentTime;

        if (timeLeft < 5 * 60) {
            const newToken = jwt.sign({id: decoded.id, role: decoded.role}, SECRET_KEY, {expiresIn: '1h'});
            res.cookie('token', newToken, {httpOnly: true, secure: true});
        }

        req.user = decoded;
        next();
    } catch (err) {
        return res.status(401).json({message: 'InvalidToken', redirect: '/login'});
    }
}

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
            age INTEGER DEFAULT 0,
            gender TEXT,
            avgDegree INTEGER DEFAULT 0,
            academicInstitution TEXT,
            totalEntries INTEGER DEFAULT 0,
            totalAnswers INTEGER DEFAULT 0,
            totalExams INTEGER DEFAULT 0,
            avgExamTime INTEGER DEFAULT 0,
            totalTrainTime INTEGER DEFAULT 0,
            avgAnswers INTEGER DEFAULT 0
        )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS authentication (
            userId TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password TEXT,
            token TEXT,
            expiredTime DATE,
            role TEXT DEFAULT 'user',
            termsAgreement BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
        )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS answers (
            answerId INTEGER PRIMARY KEY AUTOINCREMENT,
            userId TEXT,
            date TEXT,
            photoName TEXT,
            classificationSrc TEXT,
            classificationDes TEXT,
            answerSubmitTime INTEGER DEFAULT 0,
            answerChange TEXT,
            alertActivated INTEGER DEFAULT 0,
            binaryQuestion BOOLEAN DEFAULT FALSE,
            helpActivated BOOLEAN DEFAULT FALSE,
            helpTimeActivated INTEGER DEFAULT 0,
            FOREIGN KEY (userId) REFERENCES users(id)
        )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS exam (
            examId INTEGER PRIMARY KEY AUTOINCREMENT,
            userId TEXT,
            date TEXT,
            title TEXT,
            score INTEGER DEFAULT 0,
            totalExamTime INTEGER DEFAULT 0,
            FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
        )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS imageClassification (
            imageId INTEGER PRIMARY KEY AUTOINCREMENT,
            photoName TEXT,
            classification TEXT,
            rate INTEGER DEFAULT 0
        )`);
    });
}

// Terms of use endpoint
app.get('/terms', (req, res) => {
    const terms = fs.readFileSync(path.join(__dirname, 'Terms.txt'), 'utf8');
    res.send(terms);
});

// User registration
app.post('/register', async (req, res) => {
    const {email, password, age, gender, avgDegree, academicInstitution, termsAgreement} = req.body;
    if (!email || !password || !age || !gender || !avgDegree || !academicInstitution || termsAgreement === false) {
        return res.status(400).json({message: 'All fields are required'});
    }

    db.get('SELECT email FROM authentication WHERE email = ?', [email], async (err, row) => {
        if (err) {
            console.error('Error querying the database:', err.message);
            return res.status(500).json({message: 'Server error'});
        }

        if (row) {
            return res.status(409).json({message: 'User already exists. Please log in.', redirect: '/login'});
        }

        const hashedPassword = await bcrypt.hash(password, 10);
        const userId = uuidv4();

        db.run('INSERT INTO users (id, age, gender, avgDegree, academicInstitution) VALUES (?, ?, ?, ?, ?)', [userId, age, gender, avgDegree, academicInstitution], (err) => {
            if (err) {
                return res.status(500).json({message: 'Error registering new user in Users table: ' + err.message});
            }
            db.run('INSERT INTO authentication (userId, email, password, termsAgreement, role) VALUES (?, ?, ?, ?, "user")', [userId, email, hashedPassword, termsAgreement], (authErr) => {
                if (authErr) {
                    return res.status(500).json({message: 'Error registering new user in Authentication table: ' + authErr.message});
                }
                res.status(200).json({message: 'User registered successfully', redirect: '/login'});
            });
        });
    });
});

// User login
app.post('/login', (req, res) => {
    const { email, password } = req.body;
    const sql = `SELECT userId, password, role FROM authentication WHERE email = ?`;
    const updateEntries = `UPDATE users SET totalEntries = totalEntries + 1 WHERE id = ?`;
    let tempUser;

    db.get(sql, [email], async (err, user) => {
        if (err) {
            console.error('Database error:', err.message);
            return res.status(500).json({ message: 'Error on server side: ' + err.message });
        }
        if (!user) {
            return res.status(404).json({ message: 'User not found' });
        }
        if (await bcrypt.compare(password, user.password)) {
            const token = jwt.sign({ id: user.userId, role: user.role }, SECRET_KEY, { expiresIn: '1h' });
            res.cookie('token', token, { httpOnly: true, secure: true });
            res.cookie('userId', user.userId, { httpOnly: true, secure: true });
            res.status(200).json({ redirect: '/chooseModel', message: 'Login successful', role: user.role });
            db.run(updateEntries, [user.userId],async (err) => {
                if (err) {
                    console.error('Error updating totalEntries:', err.message);
                } else {
                    console.log(`totalEntries updated for userId ${user.userId}`);
                }
            });


        } else {
            res.status(401).json({ message: 'Invalid email or password' });
        }
    });

});

// Protected routes using verifyToken middleware
app.use('/training', verifyToken);
app.use('/pre-training', verifyToken);
app.use('/chooseModelAdmin', verifyToken);
app.use('/classifiedImagesAdmin', verifyToken);
app.use('/random-image-classification', verifyToken);
app.use('/random-image', verifyToken);
app.use('/classifiedImages', verifyToken);
app.use('/classify-image', verifyToken);
app.use('/chooseModel', verifyToken);

// Choose model (POST)
app.post('/chooseModel', verifyToken, (req, res) => {
    const action = req.body.action;
    switch (action) {
        case 'classifiedImages':
            if (req.user.role !== 'admin') {
                return res.status(403).json({
                    redirect: '/chooseModel',
                    message: 'You do not have permission to access this page'
                });
            }
            res.status(200).json({redirect: '/classifiedImagesAdmin', message: 'Redirecting to classified images'});
            break;
        case 'Single Training':
            res.status(200).json({redirect: '/pre-training', message: 'Redirecting to pre-training page'});
            break;
        case 'Test':
            res.status(200).json({redirect: '/test', message: 'Redirecting to test page'});
            break;
        default:
            res.status(404).json({message: 'Action not found'});
    }
});

// Serve classifiedImagesAdmin.html
app.get('/classifiedImagesAdmin', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'classifiedImagesAdmin.html'));
});

// Serve other static pages
app.get('/login', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'views', 'login.html')));
app.get('/register', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'views', 'register.html')));
app.get('/chooseModel', verifyToken, (req, res) => {
    if (req.cookies.token) {
        const decoded = jwt.verify(req.cookies.token, SECRET_KEY);
        if (decoded.role === 'admin') {
            return res.redirect('/chooseModelAdmin');
        }
    }
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'chooseModel.html'));
});
app.get('/chooseModelAdmin', verifyToken, (req, res) => {
    const token = req.cookies.token;
    if (!token) return res.status(401).send('Access Denied');
    const decoded = jwt.verify(token, SECRET_KEY);
    if (decoded.role !== 'admin') {
        return res.status(403).send('You do not have permission to access this page');
    } else {
        res.sendFile(path.join(__dirname, '..', 'public', 'views', 'chooseModelAdmin.html'));
    }
});

// Serve the pre-train page
app.get('/pre-training', (req, res) => {
    const token = req.cookies.token;
    if (!token) return res.status(401).send('Access Denied');
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'preTraining.html'));
});

// Serve the pre-training page
app.post('/pre-training', verifyToken, (req, res) => {
    res.json({redirect: '/training', message: 'Pre-training completed successfully'});
});

// Serve the training page
app.get('/training', checkToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'training.html'));
});

// Serve the training page
app.post('/training', verifyToken, (req, res) => {
    const {
        photoName,
        classificationSrc,
        classificationDes,
        answerTime,
        answerChange,
        alertActivated,
        submissionType,
        helpButtonClicks
    } = req.body;

    const userId = req.user.id; // Assuming user ID is stored in the token and extracted by verifyToken middleware

    const date = new Date().toISOString();

    const sql = `
        INSERT INTO answers (
            userId, date, photoName, classificationSrc, classificationDes, 
            answerSubmitTime, answerChange, alertActivated, binaryQuestion, 
            helpActivated, helpTimeActivated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;

    const params = [
        userId,
        date,
        photoName,
        classificationSrc,
        classificationDes,
        answerTime,
        answerChange,
        alertActivated,
        submissionType === 'automatic' ? 1 : 0,
        helpButtonClicks.length > 0 ? 1 : 0,
        helpButtonClicks.length > 0 ? helpButtonClicks[0] : null
    ];

    db.run(sql, params, function (err) {
        if (err) {
            console.error('Error inserting answer into database:', err.message);
            return res.status(500).json({message: 'Error inserting answer into database'});
        }

        // Update user statistics
        db.serialize(() => {
            // Update totalAnswers
            db.run('UPDATE users SET totalAnswers = totalAnswers + 1 WHERE id = ?', [userId], (err) => {
                if (err) {
                    console.error('Error updating totalAnswers:', err.message);
                }
            });

            // Update avgAnswers
            const updateAvgAnswersSql = `
                UPDATE users
                SET avgAnswers = (
                    SELECT COUNT(*) * 1.0 / u.totalAnswers
                    FROM answers a
                    JOIN users u ON a.userId = u.id
                    WHERE a.classificationSrc = a.classificationDes AND u.id = ?
                )
                WHERE id = ?
            `;
            db.run(updateAvgAnswersSql, [userId, userId], (err) => {
                if (err) {
                    console.error('Error updating avgAnswers:', err.message);
                }
            });
        });

        res.status(200).json({message: 'Answer recorded successfully'});
    });
});


// Endpoint to handle INFO page
app.get('/info', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'info.html'));
});

// API to handle image classification from classifiedImagesAdmin.html
app.post('/classify-image', verifyToken, (req, res) => {
    const {fileName, category} = req.body;
    console.log(`Classifying image ${fileName} as ${category}`);
    const sourcePath = path.join(__dirname, '..', 'public', 'img', 'bankPhotos', fileName);
    const destPath = path.join(__dirname, '..', 'public', 'img', 'graded', category, fileName);
    const folderPath = path.join(__dirname, '..', 'public', 'img', 'graded', category);
    if (!fs.existsSync(folderPath)) {
        fs.mkdirSync(folderPath, {recursive: true});
    }
    fs.rename(sourcePath, destPath, (err) => {
        if (err) {
            console.error('Error moving file:', err.message);
            return res.status(500).send('Failed to classify image');
        }
    });
    db.run('INSERT INTO imageClassification (photoName, classification) VALUES (?, ?)', [fileName, category], (err) => {
        if (err) {
            console.error('Error inserting classification:', err.message);
            return res.status(500).send('Failed to classify image');
        }
    });
    res.send(`Image ${fileName} classified as ${category}`);
});

// Endpoint to handle image classification for admins only, classification only.
app.get('/random-image-classification', (req, res) => {
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
        res.json({imagePath: `../img/bankPhotos/${imagePath}`});
    });
});

// Endpoint to handle training page, choose a random image for training
app.get('/random-image', verifyToken, (req, res) => {
    const foldersDir = path.join(__dirname, '..', 'public', 'img', 'graded');
    fs.readdir(foldersDir, {withFileTypes: true}, (err, dirents) => {
        if (err) {
            console.error('Error reading folders:', err);
            return res.status(500).send('Failed to load image folders');
        }
        const validFolders = [];
        for (const dirent of dirents) {
            if (dirent.isDirectory()) {
                validFolders.push(dirent.name);
            }
        }
        if (validFolders.length === 0) {
            return res.status(404).send('No image folders found');
        }
        let randomImagePath = '';
        let foundImage = false;
        const checkFolders = (index) => {
            if (index >= validFolders.length) {
                if (!foundImage) {
                    return res.status(404).send('No images found in any folder');
                }
                return;
            }
            const randomFolder = validFolders[Math.floor(Math.random() * validFolders.length)];
            const imagesDir = path.join(foldersDir, randomFolder);
            fs.readdir(imagesDir, (err, files) => {
                if (err) {
                    console.error('Error reading files:', err);
                    return res.status(500).send('Failed to load images');
                }
                if (files.length > 0) {
                    const randomIndex = Math.floor(Math.random() * files.length);
                    randomImagePath = path.join('..', 'img', 'graded', randomFolder, files[randomIndex]);
                    foundImage = true;
                    return res.json({imagePath: randomImagePath});
                }
                checkFolders(index + 1);
            });
        };
        checkFolders(0);
    });
});

// Main page and user data endpoints
app.get('/main', verifyToken, (req, res) => {
    if (req.user.role === 'admin') {
        return res.json({redirect: '/chooseModelAdmin', message: 'redirect to main'});

    }
    res.json({redirect: '/chooseModel', message: 'redirect to main'});
});

app.get('/user-data', verifyToken, (req, res) => {
    res.json({redirect: '/info', message: 'redirect to user data'});
});

app.get('/info', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'info.html'));
});

app.get('/info/data', verifyToken, (req, res) => {
    const userId = req.cookies.userId;
    if (!userId) {
        return res.status(400).json({message: 'No userId found in request'});
    }
    const sql = `
        SELECT photoName, classificationSrc, classificationDes
        FROM answers
        WHERE userId = ?
    `;
    db.all(sql, [userId], (err, rows) => {
        if (err) {
            console.error('Database error:', err.message);
            return res.status(500).send('Server error while fetching user data');
        }
        if (rows.length === 0) {
            return res.status(404).send('No answers found for the given user');
        }
        res.json(rows); // Send the relevant data back to the client
    });
});

// Serve sign-up page
app.get('/sign-up', (req, res) => {
    res.json({redirect: '/register', message: 'redirect to sign-up'});
});

// Serve sign-in page
app.get('/sign-in', (req, res) => {
    res.json({redirect: '/login', message: 'redirect to sign-in'});
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
