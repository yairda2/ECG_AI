// Description: This file contains the server-side code for the ECG application.
// Author: Yair Davidof & Elyasaf Sinvani.
// region Imports
const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const sqlite3 = require('sqlite3').verbose();
const cookieParser = require('cookie-parser');
const {v4: uuidv4} = require('uuid');
const path = require('path');
const fs = require('fs');
const nodemailer = require('nodemailer');
const app = express();
const cors = require('cors');
const verifyToken = require('./authMiddleware');
const config = require('../config/config');
const { exec } = require('child_process'); // Import child_process module

const PORT = config.server.port || 3000;
const SECRET_KEY = config.secret_key.key;
const isSecure = process.env.NODE_ENV === 'production';

const corsOptions = {
    origin: ['http://localhost:3000', 'http://10.0.0.28:3000'],
    credentials:true,
};
// endregion Imports

// region Middleware setup
app.use(express.json());
app.use(express.static(path.join(__dirname, '..', 'public')));
app.use('/img', express.static(path.join(__dirname, '..', 'public', 'img')));
// give the user access to the graphs and dir
app.use('/graphs', express.static(path.join(__dirname, 'graphs')));
app.use(cookieParser());
app.use(express.urlencoded({ extended: true }));
app.use(cors(corsOptions));

// Middleware to decode URL-encoded paths
app.use((req, res, next) => {
    req.url = decodeURIComponent(req.url);
    next();
});
// endregion Middleware setup

// region Database setup
const db = new sqlite3.Database('./database.db', sqlite3.OPEN_READWRITE | sqlite3.OPEN_CREATE, (err) => {
    if (err) {
        console.error('Error opening database:', err.message);
    } else {
        console.log('Connected to the SQLite database.');
        createTables();
        insertDefaultData();
    }
});

// Function to create necessary database tables
function createTables() {
    db.serialize(() => {
        db.run(`
            CREATE TABLE IF NOT EXISTS authentication (
                userId TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                password TEXT,
                token TEXT,
                expiredTime DATE,
                role TEXT DEFAULT 'user',
                termsAgreement BOOLEAN DEFAULT FALSE,
                notification BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
            )`);

        db.run(`
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            age INTEGER DEFAULT 0,
            gender TEXT,
            avgDegree INTEGER DEFAULT 0,
            academicInstitution TEXT,
            totalEntries INTEGER DEFAULT 0,
            totalExams INTEGER DEFAULT 0,
            avgExamTime INTEGER DEFAULT 0,
            totalAnswers INTEGER DEFAULT 0,
            totalTrainTime REAL DEFAULT 0,
            userRate INTEGER DEFAULT 0,
            rank TEXT,  -- Rank of the user ban-choler or master)
            source TEXT,  -- How the user heard about the app
            ecgKnowledge BOOLEAN DEFAULT 0,  -- Does the user have knowledge in ECG
            knowledgeLevel TEXT , -- The level of knowledge in ECG
            feedback TEXT

        )`);



        db.run(`
            CREATE TABLE IF NOT EXISTS answers (
                answerId INTEGER PRIMARY KEY AUTOINCREMENT,
                userId TEXT,
                date TEXT,
                photoName TEXT,
                classificationSetSrc TEXT,
                classificationSubSetSrc TEXT,
                classificationSetDes TEXT,
                classificationSubSetDes TEXT,
                answerSubmitTime INTEGER DEFAULT 0,
                helpActivated BOOLEAN DEFAULT FALSE,
                helpTimeActivated INTEGER DEFAULT 0,
                FOREIGN KEY (userId) REFERENCES users(id)
            )`);

        db.run(`
            CREATE TABLE IF NOT EXISTS examAnswers (
                examId INTEGER,
                userId TEXT,
                date TEXT,
                answerNumber INTEGER,
                photoName TEXT,
                classificationSetSrc TEXT,
                classificationSubSetSrc,
                classificationSetDes TEXT,
                answerSubmitTime INTEGER DEFAULT 0,
                PRIMARY KEY (examId, userId, answerNumber),
                FOREIGN KEY (userId) REFERENCES users(id),
                FOREIGN KEY (examId) REFERENCES exam(examId)
            )`);

        db.run(`
            CREATE TABLE IF NOT EXISTS exam (
                examId TEXT PRIMARY KEY,
                userId TEXT,
                date TEXT,
                severalQuestions INTEGER DEFAULT 0,
                score INTEGER DEFAULT 0,
                totalExamTime INTEGER DEFAULT 0,
                type TEXT CHECK(type IN ('binary', 'hath', 'full')),
                FOREIGN KEY (userId) REFERENCES users(id) ON DELETE CASCADE
            )`);

        db.run(`
            CREATE TABLE IF NOT EXISTS imageClassification (
                imageId INTEGER PRIMARY KEY AUTOINCREMENT,
                photoName TEXT,
                classificationSet TEXT CHECK (classificationSet IN ('STEMI', 'HIGH RISK', 'LOW RISK')),
                classificationSubSet TEXT,
                rate INTEGER DEFAULT 0
            )`);

        // New table for groups
        db.run(`
            CREATE TABLE IF NOT EXISTS groups (
                groupId TEXT PRIMARY KEY,
                groupName TEXT,
                createdDate TEXT,
                userId TEXT,
                FOREIGN KEY (userId) REFERENCES users(id)
            )
        `);

        // New table for users in groups
        db.run(`
            CREATE TABLE IF NOT EXISTS userGroups (
                groupId TEXT,
                userId TEXT,
                FOREIGN KEY (groupId) REFERENCES groups(groupId),
                FOREIGN KEY (userId) REFERENCES users(id),
                PRIMARY KEY (groupId, userId)
            )`);
    });
}

// Insert default data into the database, authentication table
function insertDefaultData() {
    const password = '12345678';
    const hashedPassword = bcrypt.hash(password, 10);
    const userId = uuidv4();
    const email = 'YISHAY121@gmail.com';
    const gender = 'male';
    const role = 'admin';
    const termsAgreement = true;
    const college = 'Technion';
    const avgDegree = 0;
    const age = 0;

    // Insert default admin user, only if it doesn't already exist
    db.get('SELECT email FROM authentication WHERE email = ?', [email], (err, row) => {
        if (err) {
            console.error('Error querying the database:', err.message);
            return;
        }

        if (row) {
            return;
        }

        hashedPassword.then((hash) => {
            db.run('INSERT INTO users (id, age, gender, avgDegree, academicInstitution) VALUES (?, ?, ?, ?, ?)',
                [userId, age, gender, avgDegree, college], (err) => {
                    if (err) {
                        console.error('Error inserting default data into users table:', err.message);
                    }

                    db.run('INSERT INTO authentication (userId, email, password, role, termsAgreement) VALUES (?, ?, ?, ?, ?)',
                        [userId, email, hash, role, termsAgreement], (err) => {
                            if (err) {
                                console.error('Error inserting default data into authentication table:', err.message);
                            }
                        });

                });
        });

    });
}

// endregion Database setup

// region Helper functions
function checkToken(req, res, next) {
    const token = req.cookies.token;
    if (!token) return res.status(401).json({ message: 'NoToken', redirect: '/login' });

    try {
        const decoded = jwt.verify(token, SECRET_KEY);
        const currentTime = Math.floor(Date.now() / 1000);
        const expirationTime = decoded.exp;
        const timeLeft = expirationTime - currentTime;

        if (timeLeft < 5 * 60) {  // If less than 5 minutes left, renew the token
            const newToken = jwt.sign({ id: decoded.id, role: decoded.role }, SECRET_KEY, { expiresIn: '1h' });
            res.cookie('token', newToken, { httpOnly: true, secure: true });
        }

        req.user = decoded;
        next();
    } catch (err) {
        if (err.name === 'TokenExpiredError') {
            return res.status(401).json({ message: 'TokenExpired', redirect: '/login' });
        }
        return res.status(401).json({ message: 'InvalidToken', redirect: '/login' });
    }
}

async function getClassificationValuesSrc(photoName) {
    const query = `SELECT classificationSet AS classificationSetSrc, classificationSubSet AS classificationSubSetSrc 
                   FROM imageClassification WHERE photoName = ?`;

    return new Promise((resolve, reject) => {
        db.get(query, [photoName], (err, row) => {
            if (err) {
                return reject(err);
            }
            resolve(row);
        });
    });
}

async function getClassificationValuesDes(classificationDes) {
    if (classificationDes === 'LOW RISK') {
        return { classificationSetDes: classificationDes, classificationSubSetDes: null };
    } else if (['Septal', 'Anterior', 'Lateral', 'Inferior'].includes(classificationDes)) {
        return { classificationSetDes: 'STEMI', classificationSubSetDes: classificationDes };
    } else if (['Hyperacute', 'DeWinters', 'LossOfBalance', 'Wellens', 'TInversion', 'Avrste'].includes(classificationDes)) {
        return { classificationSetDes: 'HIGH RISK', classificationSubSetDes: classificationDes };
    } else {
        return {}; // Return an empty object if no conditions are met
    }
}

function insertClassification(fileName, classificationSet, classificationSubSet) {
    const sql = `
        INSERT INTO imageClassification (photoName, classificationSet, classificationSubSet)
        VALUES (?, ?, ?)
    `;
    db.run(sql, [fileName, classificationSet, classificationSubSet], (err) => {
        if (err) {
            console.error('Error inserting image classification into database:', err.message);
        }
    });
}

function checkUserExist(id) {
    const sql = `SELECT id FROM users WHERE id = ?`;
    db.get(sql, [id], (err, row) => {
        if (err) {
            console.error('Error querying the database:', err.message);
            return false;
        }
        return row;
    });
}

// endregion Helper functions

// region Get endpoints
// Login page
app.get('/login', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'views', 'login.html')));

// Register page
app.get('/register', (req, res) => res.sendFile(path.join(__dirname, '..', 'public', 'views', 'register.html')));

// Terms text data
app.get('/terms', (req, res) => {
    const terms = fs.readFileSync(path.join(__dirname, 'Terms.txt'), 'utf8');
    res.send(terms);
});

// Admin classified images page
app.get('/classifiedImagesAdmin', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'classifiedImagesAdmin.html'));
});

// Main page
app.get('/chooseModel', verifyToken, (req, res) => {
    if (req.cookies.token) {
        const decoded = jwt.verify(req.cookies.token, SECRET_KEY);
        if (decoded.role === 'admin') {
            return res.redirect('/chooseModelAdmin');
        }
    }
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'chooseModel.html'));
});

// Admin page
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

// Training page
app.get('/training', checkToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'training.html'));
});

// Pre-test
app.get('/pre-test', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'preTest.html'));
});

// Test page
app.get('/test', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'test.html'));
});

// User data page
app.get('/info', verifyToken, (req, res) => {
    // selction by user type
    if (req.user.role === 'user') {
        res.sendFile(path.join(__dirname, '..', 'public', 'views', 'info.html'));
    }
    else {
        res.sendFile(path.join(__dirname, '..', 'public', 'views', 'groupManagement.html'));
    }
});

// This endpoint is used to get the image path for the image classification task,
// Those are not classified yet
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
        res.json({ imagePath: `../img/bankPhotos/${imagePath}` });
    });
});

// Those images are already classified
// Get random image for training and test
app.get('/random-image', verifyToken, (req, res) => {
    const getClassifiedImagesQuery = `
        SELECT photoName FROM imageClassification
    `;

    db.all(getClassifiedImagesQuery, (err, rows) => {
        if (err) {
            console.error('Error querying classified images:', err);
            return res.status(500).send('Failed to load classified images');
        }

        if (rows.length === 0) {
            return res.status(404).send('No classified images found');
        }

        const classifiedImages = rows.map(row => row.photoName);

        const randomIndex = Math.floor(Math.random() * classifiedImages.length);
        const randomImagePath = classifiedImages[randomIndex];
        const sql = `
            SELECT classificationSet, classificationSubSet
            FROM imageClassification
            WHERE photoName = ?
        `;
        db.get(sql, [randomImagePath], (err, row) => {
            if (err) {
                console.error('Error querying image classification:', err);
                return res.status(500).send('Failed to load image classification');
            }
            if (!row) {
                return res.status(404).send('Image classification not found');
            }
            const correctAnswer = row.classificationSubSet === null ? row.classificationSet : row.classificationSubSet;
            res.json({
                imagePath: `../img/graded/${row.classificationSet}/${row.classificationSubSet || ''}/${randomImagePath}`,
                correctAnswer: correctAnswer
            });
        });
    });
});

// Main page, redirect to chooseModel or chooseModelAdmin
app.get('/main', verifyToken, (req, res) => {
    if (req.user.role === 'admin') {
        return res.json({ redirect: '/chooseModelAdmin', message: 'redirect to main' });
    }
    res.json({ redirect: '/chooseModel', message: 'redirect to main' });
});

// User data page, redirect to info
app.get('/user-data', verifyToken, (req, res) => {
    res.json({ redirect: '/info', message: 'redirect to user data' });
});

// Data for user info page
app.get('/info/data', (req, res) => {
    const userId = req.cookies.userId;
    const sql = "SELECT photoName, classificationSetSrc, classificationSubSetSrc, classificationSetDes, classificationSubSetDes, answerSubmitTime, helpActivated FROM answers WHERE userId = ?";
    db.all(sql, userId, (err, rows) => {
        if (err) {
            res.status(400).json({ "error": err.message });
            return;
        }
        res.json(rows);
    });
});

// Serve images for image user info page
app.get('/img/graded/:set/:photo', (req, res) => {
    const set = req.params.set.toUpperCase()
    const photo = req.params.photo;
    const imagePath = path.join(__dirname, '..', 'public', 'img', 'graded', set, photo);
    res.sendFile(imagePath);
});

// Sign up, redirect to register
app.get('/sign-up', (req, res) => {
    res.json({ redirect: '/register', message: 'redirect to sign-up' });
});

// Sign in, redirect to log in
app.get('/sign-in', (req, res) => {
    res.json({ redirect: '/login', message: 'redirect to sign-in' });
});

// Serve post-test page
app.get('/postTest', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'postTest.html'));
});

// Route to serve detailedResults.html
app.get('/detailedResults', (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'detailedResults.html'));
});

// Route to serve groupManagement.html
app.get('/groupManagement', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'groupManagement.html'));
});

// Serve Test Sessions HTML Page
app.get('/testSessions', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'testSessions.html'));
});

// Serve Training Sessions HTML Page
app.get('/trainingSessions', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'trainingSessions.html'));
});

// Endpoint to get training sessions data
app.get('/getTrainingSessions', verifyToken, (req, res) => {
    const userId = req.user.id;
    const sql = `
                SELECT answerId AS id, 
               date(datetime(date, 'localtime')) AS date, 
               answerSubmitTime AS timeSpent, 
               COUNT(*) AS numberOfTasks,
               photoName AS imageUrl,
               CASE 
                   WHEN classificationSetSrc = classificationSetDes 
                        AND (classificationSubSetSrc = classificationSubSetDes OR 
                             (classificationSubSetSrc IS NULL AND classificationSubSetDes IS NULL))
                   THEN 1
                   ELSE 0
               END AS correct
        FROM answers
        WHERE userId = ?
        GROUP BY date, answerId
        ORDER BY date DESC;
        `;

    db.all(sql, [userId], (err, rows) => {
        if (err) {
            return res.status(500).json({ message: 'Error fetching training sessions', error: err });
        }
        res.status(200).json(rows);
    });
});

app.get('/getTrainingDetails', verifyToken, (req, res) => {
    const sessionId = req.query.sessionId;
    const sql = `
        SELECT date, photoName AS imageUrl, classificationSetSrc, classificationSubSetSrc, 
               classificationSetDes, answerSubmitTime AS timeSpent, helpActivated
        FROM answers
        WHERE answerId = ? AND userId = ?
    `;

    db.get(sql, [sessionId, req.user.id], (err, row) => {
        if (err) {
            console.error('Error fetching training details:', err.message);
            return res.status(500).json({ message: 'Error fetching training details' });
        }
        if (!row) {
            return res.status(404).json({ message: 'Training session not found' });
        }

        // Ensure the correct format for the image URL
        row.imageUrl = row.classificationSubSetSrc
            ? `/img/graded/${row.classificationSetSrc}/${row.classificationSubSetSrc}/${row.imageUrl}`
            : `/img/graded/${row.classificationSetSrc}/${row.imageUrl}`;

        res.status(200).json(row);
    });
});



// Endpoint to get detailed training results
app.get('/detailedTrainingResult', verifyToken, (req, res) => {
    const photoName = req.query.photoName;
    const sql = `
        SELECT * 
        FROM answers
        WHERE photoName = ? AND userId = ?
    `;

    db.get(sql, [photoName, req.user.id], (err, row) => {
        if (err) {
            console.error('Error fetching training result:', err.message);
            return res.status(500).json({ message: 'Error fetching training result' });
        }
        if (!row) {
            return res.status(404).json({ message: 'Training result not found' });
        }

        res.render('detailedResults', {
            photoName: row.photoName,
            date: row.date,
            classificationSetSrc: row.classificationSetSrc,
            classificationSubSetSrc: row.classificationSubSetSrc,
            classificationSetDes: row.classificationSetDes,
            answerSubmitTime: row.answerSubmitTime,
            helpActivated: row.helpActivated
        });
    });
});

// Endpoint to get training image by ID
app.get('/getTrainingImage/:id', verifyToken, (req, res) => {
    const answerId = req.params.id;
    const sql = `
        SELECT photoName, classificationSetSrc, classificationSubSetSrc
        FROM answers
        WHERE answerId = ?`;

    db.get(sql, [answerId], (err, row) => {
        if (err) {
            return res.status(500).json({ message: 'Error fetching image URL' });
        }
        if (!row) {
            return res.status(404).json({ message: 'Image not found' });
        }

        const imageUrl = row.classificationSubSetSrc
            ? `/img/graded/${row.classificationSetSrc}/${row.classificationSubSetSrc}/${row.photoName}`
            : `/img/graded/${row.classificationSetSrc}/${row.photoName}`;

        res.status(200).json({ imageUrl });
    });
});

// Serve Test Sessions HTML Page
app.get('/testSessions', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'testSessions.html'));
});

// Endpoint to get test sessions
app.get('/getTestSessions', verifyToken, (req, res) => {
    const userId = req.user.id;
    const sql = `
        SELECT examId, 
               strftime('%Y-%m-%d', date) as date, 
               score AS grade, 
               severalQuestions AS numberOfAnswers, 
               (SELECT COUNT(*) 
                FROM examAnswers 
                WHERE examAnswers.examId = exam.examId 
                AND classificationSetSrc = classificationSetDes) AS correctAnswers
        FROM exam
        WHERE userId = ?`;

    db.all(sql, [userId], (err, rows) => {
        if (err) {
            return res.status(500).json({ message: 'Error fetching test sessions' });
        }
        res.status(200).json(rows);
    });
});

// Endpoint to get test details
app.get('/getTestDetails', verifyToken, (req, res) => {
    const examId = req.query.examId;
    const sql = `
        SELECT date, score AS grade, severalQuestions AS numberOfAnswers, 
        (SELECT COUNT(*) FROM examAnswers WHERE examAnswers.examId = exam.examId AND classificationSetSrc = classificationSetDes) AS correctAnswers
        FROM exam
        WHERE examId = ?`;

    db.get(sql, [examId], (err, row) => {
        if (err) {
            console.error('Error fetching test details:', err.message);
            return res.status(500).json({ message: 'Error fetching test details' });
        }
        if (!row) {
            return res.status(404).json({ message: 'Test session not found' });
        }
        res.status(200).json(row);
    });
});


// endregion Get endpoints

// region Post endpoints
// region Post endpoints
app.post('/register', async (req, res) => {
    const { email, password, age, gender, avgDegree, academicInstitution, termsAgreement, rank, source, ecgKnowledge, knowledgeLevel } = req.body;
    if (!email || !password || !age || !gender || !avgDegree || !academicInstitution || termsAgreement === false || !rank || !source || !knowledgeLevel) {
        return res.status(400).json({ message: 'All fields are required' });
    }

    db.get('SELECT email FROM authentication WHERE email = ?', [email], async (err, row) => {
        if (err) {
            console.error('Error querying the database:', err.message);
            return res.status(500).json({ message: 'Server error' });
        }

        if (row) {
            return res.status(409).json({ message: 'User already exists. Please log in.', redirect: '/login' });
        }

        const hashedPassword = await bcrypt.hash(password, 10);
        const userId = uuidv4();

        db.run('INSERT INTO users (id, age, gender, avgDegree, academicInstitution, rank, source, ecgKnowledge, knowledgeLevel) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [userId, age, gender, avgDegree, academicInstitution, rank, source, ecgKnowledge, knowledgeLevel], (err) => {
                if (err) {
                    return res.status(500).json({ message: 'Error registering new user in Users table: ' + err.message });
                }
                db.run('INSERT INTO authentication (userId, email, password, termsAgreement, role) VALUES (?, ?, ?, ?, "user")', [userId, email, hashedPassword, termsAgreement], (authErr) => {
                    if (authErr) {
                        return res.status(500).json({ message: 'Error registering new user in Authentication table: ' + authErr.message });
                    }
                    res.status(200).json({ message: 'User registered successfully', redirect: '/login' });
                });
            });
    });
});

app.post('/login', (req, res) => {
    const { email, password } = req.body;
    const redirectUrl = req.query.redirectUrl || '/chooseModel';
    const sql = `SELECT userId, password, role FROM authentication WHERE email = ?`;
    const updateEntries = `UPDATE users SET totalEntries = totalEntries + 1 WHERE id = ?`;

    db.get(sql, [email], async (err, user) => {
        if (err) {
            console.error('Database error:', err.message);
            return res.status(500).json({ message: 'Error on server side: ' + err.message });
        }
        if (!user) {
            return res.status(404).json({ message: 'User not found' });
        }
        if (await bcrypt.compare(password, user.password)) {
            const token = jwt.sign({ id: user.userId, role: user.role }, config.secret_key.key, { expiresIn: '1h' });
            res.cookie('token', token, { httpOnly: true, secure: isSecure });
            res.cookie('userId', user.userId, { httpOnly: true, secure: isSecure });
            res.status(200).json({ redirect: decodeURIComponent(redirectUrl), message: 'Login successful', role: user.role });
            db.run(updateEntries, [user.userId], async (err) => {
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
            res.status(200).json({ redirect: '/classifiedImagesAdmin', message: 'Redirecting to classified images' });
            break;
        case 'Single Training':
            res.status(200).json({ redirect: '/training', message: 'Redirecting to training page' });
            break;
        case 'Test':
            res.status(200).json({ redirect: '/pre-test', message: 'Redirecting to test page' });
            break;
        default:
            res.status(404).json({ message: 'Action not found' });
    }
});

app.post('/classify-image', verifyToken, (req, res) => {
    const { fileName, classificationSet, classificationSubSet } = req.body;
    const outDir = path.join(__dirname, '..', 'public', 'img', 'graded', classificationSet, classificationSubSet || '');
    const filePath = path.join(outDir, fileName);
    const gradedDir = path.join(__dirname, '..', 'public', 'img', 'graded');
    if (!fs.existsSync(outDir)) {
        fs.mkdirSync(outDir, { recursive: true });
    }
    fs.rename(path.join(__dirname, '..', 'public', 'img', 'bankPhotos', fileName), filePath, (err) => {
        if (err) {
            console.error('Error moving image:', err.message);
            return res.status(500).json({ message: 'Error moving image' });
        }
        const checkSql = `
            SELECT photoName
            FROM imageClassification
            WHERE photoName = ?
        `;
        db.get(checkSql, [fileName], (err, row) => {
            if (err) {
                console.error('Error checking image classification:', err.message);
                return res.status(500).json({ message: 'Error checking image classification' });
            }
            if (row) {
                return res.status(409).json({ message: 'Image already classified' });
            }
            insertClassification(fileName, classificationSet, classificationSubSet);
        });
    });
    res.status(200).json({ message: 'Image classified successfully' });
});

app.post('/training', verifyToken, async (req, res) => {
    const {
        photoName,
        answerTime,
        alertActivated,
        helpButtonClicks
    } = req.body;

    if (!req.cookies.userId) {
        return res.redirect('/login?message=Please login to continue');
    }

    const userId = req.cookies.userId;
    const date = new Date().toISOString();

    const sql = `
        INSERT INTO answers (
            userId, date, photoName, classificationSetSrc, classificationSubSetSrc, classificationSetDes, classificationSubSetDes,
            answerSubmitTime, helpActivated, helpTimeActivated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `;

    async function setParams(userId, date, photoName, answerTime, alertActivated, helpButtonClicks) {
        try {
            const classificationValuesSrc = await getClassificationValuesSrc(photoName);
            const classificationValuesDes = req.body.classificationDes ? await getClassificationValuesDes(req.body.classificationDes) : {};

            return [
                userId,
                date,
                photoName,
                classificationValuesSrc.classificationSetSrc || null,
                classificationValuesSrc.classificationSubSetSrc || null,
                classificationValuesDes.classificationSetDes || null,
                classificationValuesDes.classificationSubSetDes || null,
                answerTime,
                helpButtonClicks.length > 0 ? 1 : 0,
                helpButtonClicks.length > 0 ? helpButtonClicks[0] : null
            ];
        } catch (error) {
            console.error('Error getting classification values:', error);
            throw error;
        }
    }

    try {
        const params = await setParams(userId, date, photoName, answerTime, alertActivated, helpButtonClicks);

        db.run(sql, params, function (err) {
            if (err) {
                console.error('Error inserting answer into database:', err.message);
                return res.status(500).json({ message: 'Error inserting answer into database' });
            }

            db.serialize(() => {
                db.run('UPDATE users SET totalAnswers = totalAnswers + 1 WHERE id = ?', [userId], (err) => {
                    if (err) {
                        console.error('Error updating totalAnswers:', err.message);
                    }
                });
            });

            const updateTotalTrainTime = `
                UPDATE users
                SET totalTrainTime = totalTrainTime + ?
                WHERE id = ?`;
            db.run(updateTotalTrainTime, [answerTime, userId], (err) => {
                if (err) {
                    console.error('Error updating totalTrainTime:', err.message);
                }
            });

            res.status(200).json({ message: 'Answer recorded successfully' });
        });
    } catch (error) {
        console.error('Error setting params:', error);
        res.status(500).json({ message: 'Internal server error' });
    }
});

app.post('/pre-test', verifyToken, (req, res) => {
    // Set the cookie exam number and answer number.
    const questionCount = req.body.questionCount;

    const examId = uuidv4();
    const answerNumber = 1;
    res.cookie('examId', examId, { httpOnly: true, secure: true });
    res.cookie('questionCount', questionCount, { httpOnly: true, secure: true });
    res.cookie('answerNumber', answerNumber, { httpOnly: true, secure: true });
    res.status(200).json({ message: 'Pre-test initiated successfully', redirect: '/test' });

    // Insert exam into database
    const userId = req.user.id;
    const date = new Date().toISOString();
    const severalQuestions = questionCount;
    const score = 0;
    const totalExamTime = 0;
    const type = 'binary';

    const sql = `
        INSERT INTO exam (
            examId, userId, date, severalQuestions, score, totalExamTime, type
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    `;

    const params = [
        examId,
        userId,
        date,
        severalQuestions,
        score,
        totalExamTime,
        type
    ];

    db.run(sql, params, function (err) {
        if (err) {
            console.error('Error inserting exam into database:', err.message);
        } else {
            console.log('Exam inserted successfully');
        }
    });
});

// Route to get the current question number
app.get('/current-question-number', verifyToken, (req, res) => {
    const answerNumber = req.cookies.answerNumber || 1;
    res.json({ answerNumber: answerNumber });
});

// Ensure that the `submitClassification` route also updates the `answerNumber` in the cookie
app.post('/test', verifyToken, async (req, res) => {
    const { photoName, classificationDes, answerTime } = req.body;
    const userId = req.user.id;
    const date = new Date().toISOString();
    const examId = req.cookies.examId;
    let answerNumber = parseInt(req.cookies.answerNumber, 10) || 0;
    const questionCountQuery = 'SELECT severalQuestions FROM exam WHERE examId = ?';

    db.get(questionCountQuery, [examId], async (err, row) => {
        if (err) {
            console.error('Error querying the database:', err.message);
            res.status(500).json({ message: 'Error querying the database' });
            return;
        }

        if (row) {
            const questionCount = parseInt(row.severalQuestions, 10);
            console.log(`Number of questions: ${questionCount}`);

            const sql = `
                INSERT INTO examAnswers (
                    examId, userId, date, answerNumber, photoName, classificationSetSrc, classificationSubSetSrc,
                    classificationSetDes, answerSubmitTime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`;

            try {
                const classificationValuesSrc = await getClassificationValuesSrc(photoName);
                const params = [
                    examId,
                    userId,
                    date,
                    answerNumber,
                    photoName,
                    classificationValuesSrc.classificationSetSrc || null,
                    classificationValuesSrc.classificationSubSetSrc || null,
                    classificationDes,
                    answerTime,
                ];

                db.run(sql, params, (err) => {
                    if (err) {
                        console.error('Error inserting test answer into database:', err.message);
                        return res.status(500).json({ message: 'Error inserting test answer into database' });
                    }

                    if (answerNumber === questionCount) {
                        updateExamStats(examId, userId, questionCount, (updateErr) => {
                            if (updateErr) {
                                return res.status(500).json({ message: 'Error updating exam stats' });
                            }

                            res.clearCookie('answerNumber');
                            res.status(200).json({
                                message: 'Test completed successfully',
                                redirect: '/postTest'
                            });
                        });
                    } else {
                        answerNumber++;
                        res.cookie('answerNumber', answerNumber, { httpOnly: true, secure: true });
                        res.status(200).json({
                            message: 'Test answer recorded successfully',
                            nextQuestionNumber: answerNumber
                        });
                    }
                });
            } catch (error) {
                console.error('Error getting classification values:', error);
                res.status(500).json({ message: 'Internal server error' });
            }
        } else {
            console.error('No exam found with the provided examId');
            res.status(404).json({ message: 'No exam found' });
        }
    });
});

function updateExamStats(examId, userId, questionCount, callback) {
    console.log(`Starting updateExamStats for examId: ${examId} and userId: ${userId}`);

    const updateTotalExamTime = `
        UPDATE exam
        SET totalExamTime = (
            SELECT SUM(answerSubmitTime)
            FROM examAnswers
            WHERE examId = ?
        )
        WHERE examId = ?`;

    db.run(updateTotalExamTime, [examId, examId], (err) => {
        if (err) {
            console.error('Error updating totalExamTime:', err.message);
            return callback(err);
        }
        console.log('Total exam time updated successfully.');

        const updateTotalAnswers = `
            UPDATE users
            SET totalAnswers = totalAnswers + ?
            WHERE id = ?`;

        db.run(updateTotalAnswers, [questionCount, userId], (err) => {
            if (err) {
                console.error('Error updating totalAnswers:', err.message);
                return callback(err);
            }
            console.log('Total answers count updated successfully.');

            const updateTotalExams = `
                UPDATE users
                SET totalExams = totalExams + 1
                WHERE id = ?`;

            db.run(updateTotalExams, [userId], (err) => {
                if (err) {
                    console.error('Error updating totalExams:', err.message);
                    return callback(err);
                }
                console.log('Total exams count updated successfully.');

                // Calculate totalRate and scores
                const calculateTotalRate = `
                    SELECT SUM(rate) AS totalRate
                    FROM imageClassification
                    JOIN examAnswers ON imageClassification.photoName = examAnswers.photoName
                    WHERE examAnswers.examId = ?`;

                db.get(calculateTotalRate, [examId], (err, rateResult) => {
                    if (err || !rateResult) {
                        console.error('Error calculating total rate:', err ? err.message : "No rate result found");
                        return callback(err);
                    }
                    const totalRate = rateResult.totalRate || 1; // Avoid division by zero
                    console.log(`Total Rate calculated: ${totalRate}`);

                    const calculateScore = `
                        SELECT SUM(
                            CASE
                                WHEN INSTR(LOWER(TRIM(examAnswers.classificationSetDes)), LOWER(TRIM(imageClassification.classificationSet))) > 0
                                    THEN (imageClassification.rate * 100.0 / ?)
                                ELSE 0
                            END
                        ) AS calculatedScore
                        FROM imageClassification
                        JOIN examAnswers ON imageClassification.photoName = examAnswers.photoName
                        WHERE examAnswers.examId = ?`;


                    db.get(calculateScore, [totalRate, examId], (err, scoreResult) => {
                        if (err) {
                            console.error('Error calculating score:', err.message);
                            return callback(err);
                        }
                        const score = scoreResult ? scoreResult.calculatedScore : 0;
                        console.log(`Calculated Score before updating: ${score}`);

                        const updateScore = `
                            UPDATE exam
                            SET score = ?
                            WHERE examId = ?`;

                        db.run(updateScore, [score, examId], (err) => {
                            if (err) {
                                console.error('Error updating score:', err.message);
                                return callback(err);
                            }
                            console.log('Score updated successfully.');
                            callback(null, 'Update complete'); // Assume callback accepts (error, successMessage)
                        });
                    });
                });
            });
        });
    });
}


// Endpoint to handle post-test results
app.get('/post-test-results', verifyToken, async (req, res) => {
    const examId = req.cookies.examId; // Assume examId is stored in a cookie
    const userId = req.user.id; // Retrieved from the verifyToken middleware

    try {
        const results = await getPostTestResults(examId, userId);
        res.status(200).json(results);
    } catch (error) {
        console.error('Error fetching post-test results:', error);
        res.status(500).json({ message: 'Internal server error' });
    }
});

// Function to fetch post-test results from the database
async function getPostTestResults(examId, userId) {
    const sql = `
        SELECT examAnswers.photoName, examAnswers.classificationSetSrc, examAnswers.classificationSetDes, examAnswers.answerSubmitTime,
            imageClassification.rate,
            CASE 
                WHEN INSTR(LOWER(TRIM(examAnswers.classificationSetDes)), LOWER(TRIM(imageClassification.classificationSet))) > 0 
                THEN (imageClassification.rate * 100.0 / 
                      (SELECT SUM(rate) 
                       FROM imageClassification 
                       JOIN examAnswers 
                       ON imageClassification.photoName = examAnswers.photoName 
                       WHERE examAnswers.examId = ?))
                ELSE 0 
            END AS score
        FROM examAnswers
        JOIN imageClassification ON examAnswers.photoName = imageClassification.photoName
        WHERE examAnswers.examId = ? AND examAnswers.userId = ?;
    `;

    return new Promise((resolve, reject) => {
        db.all(sql, [examId, examId, userId], (err, rows) => {
            if (err) {
                return reject(err);
            }

            // Log the data retrieved for debugging
            console.log("Rows fetched:", rows);

            let totalQuestions = rows.length;
            let correctAnswers = rows.filter(row => {
                // if SetSrc = SetDes = LOW RISK or if SetSrc = (STEMI or HIGH RISK) and SetDes = HIGH RISK/STEMI
                return (row.classificationSetSrc === row.classificationSetDes && row.classificationSetDes === 'LOW RISK') ||
                    (['STEMI', 'HIGH RISK'].includes(row.classificationSetSrc) && row.classificationSetDes === 'HIGH RISK/STEMI');
            }).length;

            let totalTime = rows.reduce((acc, row) => acc + row.answerSubmitTime, 0);
            let grade = rows.reduce((acc, row) => acc + row.score, 0);

            // Log results for debugging
            console.log("Total Questions:", totalQuestions);
            console.log("Correct Answers:", correctAnswers);
            console.log("Total Time:", totalTime);
            console.log("Grade:", grade);

            resolve({
                totalQuestions,
                correctAnswers,
                totalTime,
                grade: grade.toFixed(2),
                answers: rows
            });
        });
    });
}

// Route to serve detailedResults.html
app.get('/detailedResults', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'detailedResults.html'));
});

// Endpoint to fetch detailed post-test results
app.get('/post-test-detailed-results', verifyToken, async (req, res) => {
    const examId = req.cookies.examId;
    const userId = req.user.id;

    try {
        const results = await getPostTestResults(examId, userId);
        res.status(200).json(results);
    } catch (error) {
        console.error('Error fetching detailed post-test results:', error);
        res.status(500).json({ message: 'Internal server error' });
    }
});

// New endpoints for group management
// Existing imports and middleware setup ...

// Endpoint to create a new group
// Endpoint to create a new group
app.post('/createGroup', verifyToken, (req, res) => {
    const { groupName } = req.body;
    const userId = req.user.id;

    // Check if the group name already exists for this user
    const checkSql = `SELECT * FROM groups WHERE groupName = ? AND userId = ?`;
    db.get(checkSql, [groupName, userId], (err, row) => {
        if (err) {
            console.error('Error checking group name:', err.message);
            return res.status(500).json({ message: 'Server error checking group name' });
        }

        if (row) {
            // Group with the same name already exists
            return res.status(400).json({ message: 'A group with this name already exists for your account' });
        }

        // If no group with the same name exists, proceed to create the group
        const groupId = uuidv4();
        const createdDate = new Date().toISOString();
        const insertSql = `INSERT INTO groups (groupId, groupName, createdDate, userId) VALUES (?, ?, ?, ?)`;

        db.run(insertSql, [groupId, groupName, createdDate, userId], (err) => {
            if (err) {
                console.error('Error creating group:', err.message);
                return res.status(500).json({ message: 'Error creating group' });
            }
            res.status(200).json({ message: 'Group created successfully', groupId });
        });
    });
});

// Endpoint to get all groups
app.get('/groups', verifyToken, (req, res) => {
    const sql = `SELECT g.groupId, g.groupName, g.createdDate, COUNT(ug.userId) as numberOfUsers
                 FROM groups g
                 LEFT JOIN userGroups ug ON g.groupId = ug.groupId
                 GROUP BY g.groupId`;
    db.all(sql, [], (err, rows) => {
        if (err) {
            console.error('Error fetching groups:', err.message);
            return res.status(500).json({ message: 'Error fetching groups' });
        }
        res.json(rows);
    });
});

// Endpoint to get group details (users in the group)
/*app.get('/groupDetails', verifyToken, (req, res) => {
    const groupId = req.query.groupId;

    const sql = `
    SELECT users.id, authentication.email
    FROM userGroups
    JOIN users ON userGroups.userId = users.id
    JOIN authentication ON users.id = authentication.userId
    WHERE userGroups.groupId = ?
    `;

    db.all(sql, [groupId], (err, rows) => {
        if (err) {
            console.error('Error fetching group details:', err.message);
            return res.status(500).json({ message: 'Error fetching group details' });
        }
        res.status(200).json(rows);
    });
});*/

// Endpoint to add a user to a group
app.post('/addUserToGroup', verifyToken, (req, res) => {
    const { groupId, selectedUsers } = req.body;

    selectedUsers.forEach(userId => {
        const checkSql = `SELECT * FROM userGroups WHERE groupId = ? AND userId = ?`;
        db.get(checkSql, [groupId, userId], (err, row) => {
            if (err) {
                console.error('Error checking user in group:', err.message);
                return res.status(500).json({ message: 'Error checking user in group' });
            }

            if (!row) {
                const insertSql = `INSERT INTO userGroups (groupId, userId) VALUES (?, ?)`;
                db.run(insertSql, [groupId, userId], (err) => {
                    if (err) {
                        console.error('Error adding user to group:', err.message);
                        return res.status(500).json({ message: 'Error adding user to group' });
                    }
                });
            }
        });
    });

    res.status(200).json({ message: 'Users added to group successfully' });
});

// Endpoint to remove a user from a group
app.delete('/removeUserFromGroup', verifyToken, (req, res) => {
    const { groupId, userId } = req.body;

    const sql = `DELETE FROM userGroups WHERE groupId = ? AND userId = ?`;
    db.run(sql, [groupId, userId], (err) => {
        if (err) {
            console.error('Error removing user from group:', err.message);
            return res.status(500).json({ message: 'Error removing user from group' });
        }
        res.status(200).json({ message: 'User removed from group successfully' });
    });
});

// Endpoint to delete a group
app.delete('/deleteGroup/:groupId', verifyToken, (req, res) => {
    const groupId = req.params.groupId;

    // Start a transaction to ensure all or nothing is deleted
    db.serialize(() => {
        db.run('BEGIN TRANSACTION');
        db.run('DELETE FROM userGroups WHERE groupId = ?', [groupId], (err) => {
            if (err) {
                db.run('ROLLBACK');
                return res.status(500).json({ message: 'Error deleting users from group' });
            }
        });

        db.run('DELETE FROM groups WHERE groupId = ?', [groupId], (err) => {
            if (err) {
                db.run('ROLLBACK');
                return res.status(500).json({ message: 'Error deleting group' });
            }
        });

        db.run('COMMIT', (err) => {
            if (err) {
                return res.status(500).json({ message: 'Error finalizing deletion' });
            }
            res.status(200).json({ message: 'Group and associated users deleted successfully' });
        });
    });
});

// Existing imports and middleware setup ...

// Serve Create Group Page
app.get('/createGroup', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'createGroup.html'));
});

// Serve Update Group Page
app.get('/updateGroup', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'updateGroup.html'));
});

// Serve Delete Group Page
app.get('/deleteGroup', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'deleteGroup.html'));
});

// Serve View Group Details Page
app.get('/viewGroupDetails', verifyToken, (req, res) => {
    res.sendFile(path.join(__dirname, '..', 'public', 'views', 'viewGroupDetails.html'));
});


app.get('/checkGroupName', verifyToken, (req, res) => {
    const groupName = req.query.groupName;
    const userId = req.user.id;

    const checkSql = `SELECT * FROM groups WHERE groupName = ? AND userId = ?`;
    db.get(checkSql, [groupName, userId], (err, row) => {
        if (err) {
            console.error('Error checking group name:', err.message);
            return res.status(500).json({ exists: false, message: 'Server error checking group name' });
        }

        if (row) {
            // Group with the same name already exists
            return res.status(200).json({ exists: true });
        } else {
            // No group with the same name exists
            return res.status(200).json({ exists: false });
        }
    });
});


// Example of dynamic search by email and academic institution

app.get('/searchStudents', verifyToken, (req, res) => {
    const query = req.query.query;
    const groupId = req.query.groupId;

    const sql = `
        SELECT users.id, authentication.email, users.academicInstitution,
        CASE WHEN userGroups.userId IS NOT NULL THEN 1 ELSE 0 END AS isInGroup
        FROM users
        JOIN authentication ON users.id = authentication.userId
        LEFT JOIN userGroups ON users.id = userGroups.userId AND userGroups.groupId = ?
        WHERE authentication.email LIKE ? OR users.academicInstitution LIKE ?
    `;

    const searchValue = `%${query}%`;

    db.all(sql, [groupId, searchValue, searchValue], (err, rows) => {
        if (err) {
            console.error('Error searching students:', err.message);
            return res.status(500).json({ message: 'Error searching students' });
        }
        res.status(200).json(rows);
    });
});


app.post('/addUsersToGroup', verifyToken, (req, res) => {
    const { groupId, studentIds } = req.body;

    // Validate groupId and studentIds
    if (!groupId || typeof groupId !== 'string' || groupId.trim() === '') {
        return res.status(400).json({ message: 'Invalid group ID.' });
    }

    if (!Array.isArray(studentIds) || studentIds.length === 0 || studentIds.some(id => !id || id.trim() === '')) {
        return res.status(400).json({ message: 'Invalid student IDs.' });
    }

    const validStudentIds = studentIds.filter(id => id && id.trim() !== '');

    db.serialize(() => {
        db.run('BEGIN TRANSACTION');

        validStudentIds.forEach(studentId => {
            const checkSql = `
                SELECT * FROM userGroups WHERE groupId = ? AND userId = ?
            `;
            db.get(checkSql, [groupId, studentId], (err, row) => {
                if (err) {
                    console.error('Error checking if user is already in group:', err.message);
                    db.run('ROLLBACK');
                    return res.status(500).json({ message: 'Error checking if user is already in group' });
                }

                if (!row) {
                    const insertSql = `
                        INSERT INTO userGroups (groupId, userId)
                        VALUES (?, ?)
                    `;
                    db.run(insertSql, [groupId, studentId], (insertErr) => {
                        if (insertErr) {
                            console.error('Error adding user to group:', insertErr.message);
                            db.run('ROLLBACK');
                            return res.status(500).json({ message: 'Error adding user to group' });
                        }
                    });
                }
            });
        });

        db.run('COMMIT', (commitErr) => {
            if (commitErr) {
                console.error('Error committing transaction:', commitErr.message);
                return res.status(500).json({ message: 'Error committing transaction' });
            }
            res.status(200).json({ message: 'Users successfully added to the group.' });
        });
    });
});


app.delete('/removeUserFromGroup', verifyToken, (req, res) => {
    const { groupId, userId } = req.body;

    const sql = `
        DELETE FROM userGroups
        WHERE userId = ? AND groupId = ?
    `;

    db.run(sql, [userId, groupId], function (err) {
        if (err) {
            console.error('Error removing user from group:', err.message);
            return res.status(500).json({ message: 'Error removing user from group' });
        }
        res.status(200).json({ message: 'User successfully removed from the group.' });
    });
});



// Endpoint to get overall group data (group vs non-group)
app.get('/groupOverallData', verifyToken, (req, res) => {
    const groupId = req.query.groupId;

    const overallDataQuery = `
        SELECT 
            (SELECT COUNT(*) FROM users) AS totalUsers,
            (SELECT COUNT(*) FROM answers) AS totalTrainingSessions,
            (SELECT COUNT(*) FROM exam) AS totalExams
    `;

    const groupDataQuery = `
        SELECT 
            (SELECT COUNT(*) FROM userGroups WHERE groupId = ?) AS groupUsers,
            (SELECT SUM(totalTrainTime) FROM users WHERE id IN (SELECT userId FROM userGroups WHERE groupId = ?)) AS totalTrainingTime,
            (SELECT COUNT(*) FROM exam WHERE userId IN (SELECT userId FROM userGroups WHERE groupId = ?)) AS groupExams
    `;

    db.get(overallDataQuery, [], (err, overallData) => {
        if (err) {
            console.error('Error fetching overall data:', err.message);
            return res.status(500).json({ message: 'Error fetching overall data' });
        }

        db.get(groupDataQuery, [groupId, groupId, groupId], (err, groupData) => {
            if (err) {
                console.error('Error fetching group data:', err.message);
                return res.status(500).json({ message: 'Error fetching group data' });
            }

            res.json({
                overallData,
                groupData
            });
        });
    });
});

// Endpoint to get group details (users in the group)
app.get('/groupDetails', verifyToken, (req, res) => {
    const groupId = req.query.groupId;

    const sql = `
    SELECT 
        users.id,
        authentication.email,
        users.totalTrainTime AS totalTrainingTime,
        COALESCE((SELECT COUNT(*) FROM exam WHERE exam.userId = users.id), 0) AS examCount,
        COALESCE((SELECT AVG(score) FROM exam WHERE exam.userId = users.id), 0) AS avgScore
    FROM userGroups
    JOIN users ON userGroups.userId = users.id
    JOIN authentication ON users.id = authentication.userId
    WHERE userGroups.groupId = ?
    `;

    db.all(sql, [groupId], (err, rows) => {
        if (err) {
            console.error('Error fetching group details:', err.message);
            return res.status(500).json({ message: 'Error fetching group details' });
        }
        res.status(200).json(rows);
    });
});


// Endpoint to get specific user details
app.get('/userDetails', verifyToken, (req, res) => {
    const userId = req.query.userId;

    const sql = `
        SELECT 
            authentication.email,
            users.age,
            users.academicInstitution,
            users.totalTrainTime,
            users.totalExams,
            users.avgExamTime,
            users.totalAnswers,
            users.rank,
            users.feedback
        FROM users
        JOIN authentication ON users.id = authentication.userId
        WHERE users.id = ?
    `;

    db.get(sql, [userId], (err, user) => {
        if (err) {
            console.error('Error fetching user details:', err.message);
            return res.status(500).json({ message: 'Error fetching user details' });
        }
        if (!user) {
            return res.status(404).json({ message: 'User not found' });
        }
        res.status(200).json(user);
    });
});


app.get('/api/groupVsNonGroup', verifyToken, (req, res) => {
    const groupId = req.query.groupId;

    const queryTotalUsers = `SELECT COUNT(*) AS totalUsers FROM users`;
    const queryGroupUsers = `SELECT COUNT(*) AS groupUsers FROM userGroups WHERE groupId = ?`;

    db.get(queryTotalUsers, [], (err, overallData) => {
        if (err) {
            console.error('Error fetching total users:', err.message);
            return res.status(500).json({ message: 'Error fetching total users' });
        }

        db.get(queryGroupUsers, [groupId], (err, groupData) => {
            if (err) {
                console.error('Error fetching group users:', err.message);
                return res.status(500).json({ message: 'Error fetching group users' });
            }

            res.json({
                groupUsers: groupData.groupUsers,
                nonGroupUsers: overallData.totalUsers - groupData.groupUsers
            });
        });
    });
});


app.get('/api/totalTrainingTime', verifyToken, (req, res) => {
    const groupId = req.query.groupId;

    const query = `
        SELECT users.id, authentication.email, users.totalTrainTime AS totalTrainingTime
        FROM userGroups
        JOIN users ON userGroups.userId = users.id
        JOIN authentication ON users.id = authentication.userId
        WHERE userGroups.groupId = ?
    `;

    db.all(query, [groupId], (err, rows) => {
        if (err) {
            console.error('Error fetching total training time:', err.message);
            return res.status(500).json({ message: 'Error fetching total training time' });
        }

        res.json(rows);
    });
});


app.get('/api/examCount', verifyToken, (req, res) => {
    const groupId = req.query.groupId;

    const query = `
        SELECT users.id, authentication.email, COUNT(exam.examId) AS examCount
        FROM userGroups
        JOIN users ON userGroups.userId = users.id
        JOIN authentication ON users.id = authentication.userId
        LEFT JOIN exam ON users.id = exam.userId
        WHERE userGroups.groupId = ?
        GROUP BY users.id
    `;

    db.all(query, [groupId], (err, rows) => {
        if (err) {
            console.error('Error fetching exam count:', err.message);
            return res.status(500).json({ message: 'Error fetching exam count' });
        }

        res.json(rows);
    });
});


app.get('/api/avgScoreComparison', verifyToken, (req, res) => {
    const groupId = req.query.groupId;

    const query = `
        SELECT users.id, authentication.email, AVG(exam.score) AS avgScore
        FROM userGroups
        JOIN users ON userGroups.userId = users.id
        JOIN authentication ON users.id = authentication.userId
        LEFT JOIN exam ON users.id = exam.userId
        WHERE userGroups.groupId = ?
        GROUP BY users.id
    `;

    db.all(query, [groupId], (err, rows) => {
        if (err) {
            console.error('Error fetching average score:', err.message);
            return res.status(500).json({ message: 'Error fetching average score' });
        }

        res.json(rows);
    });
});


app.get('/api/progressOverTime', verifyToken, (req, res) => {
    const groupId = req.query.groupId;

    const query = `
        SELECT date, COUNT(*) AS numberOfActivities
        FROM answers
        JOIN userGroups ON answers.userId = userGroups.userId
        WHERE userGroups.groupId = ?
        GROUP BY date
        ORDER BY date
    `;

    db.all(query, [groupId], (err, rows) => {
        if (err) {
            console.error('Error fetching progress over time:', err.message);
            return res.status(500).json({ message: 'Error fetching progress over time' });
        }

        res.json(rows);
    });
});


const multer = require('multer');
const upload = multer({ dest: 'uploads/' });
const { execFile } = require('child_process');

// POST route to handle image uploads
app.post('/upload-image', upload.single('image'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ success: false, message: 'No image uploaded' });
    }

    const imageExtension = path.extname(req.file.originalname);
    const imagePath = path.resolve(req.file.path);
    const imageWithExtension = imagePath + imageExtension;
    const heatmapPath = ('/heatmap.png');
    fs.rename(imagePath, imageWithExtension, (err) => {
        if (err) {
            console.error('Error renaming file:', err);
            return res.status(500).json({ success: false, message: 'Error processing image' });
        }

        const pythonScriptPath = path.resolve('../CNN/modelRN.py');

        execFile('python', [pythonScriptPath, imageWithExtension], (error, stdout, stderr) => {
            if (error) {
                console.error('Error executing Python script:', error);
                return res.status(500).json({ success: false, message: 'Error processing image' });
            }

            try {
                const outputLines = stdout.trim().split('\n');
                const jsonResponse = JSON.parse(outputLines[outputLines.length - 1]);

                console.log('Classification result:', jsonResponse.classification);
                console.log('Confidence:', jsonResponse.confidence);
                console.log('Graph URL:', jsonResponse.graphUrl);
                console.log('Heatmap URL:', heatmapPath);

                const graphUrl = jsonResponse.graphUrl;
                const heatmapUrl = heatmapPath;

                if (fs.existsSync(graphUrl)) {
                    res.json({
                        success: true,
                        result: jsonResponse.classification,
                        confidence: jsonResponse.confidence,
                        graphUrl: '/graphs/' + path.basename(graphUrl),
                        heatmapUrl: heatmapPath
                    });
                } else {
                    console.error('Graph or heatmap file not found:', graphUrl, heatmapUrl);
                    res.status(500).json({ success: false, message: 'Graph or heatmap file not found' });
                }
            } catch (err) {
                console.error('Error parsing JSON:', err);
                res.status(500).json({ success: false, message: 'Error parsing classification result' });
            }
        });
    });
});

// Route to serve the graphs directory
app.use('/graphs', express.static(path.join(__dirname, 'server', 'graphs')));





// Other CRUD endpoints and server setup ...

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on port ${PORT}`);

    /*// הרצת סקריפט פייתון לאחר שהשרת מתחיל לפעול
    exec(`python ${path.join(__dirname, 'insert_images_to_db.py')}`, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error executing script: ${error.message}`);
            return;
        }
        if (stderr) {
            console.error(`Script error: ${stderr}`);
            return;
        }
        console.log(`Script output: ${stdout}`);
    });

    // הרצת סקריפט פייתון לאחר שהשרת מתחיל לפעול
    exec(`python ${path.join(__dirname,"..", "analyzer", "rate_images.py")}`, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error executing script: ${error.message}`);
            return;
        }
        if (stderr) {
            console.error(`Script error: ${stderr}`);
            return;
        }
        console.log(`Script output: ${stdout}`);
    });*/
});