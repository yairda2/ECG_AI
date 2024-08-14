const jwt = require('jsonwebtoken');
const config = require('../config/config');

function verifyToken(req, res, next) {
    // חפש את הטוקן בקוקיז וב- Authorization header
    const token = req.cookies.token || (req.headers['authorization'] && req.headers['authorization'].replace('Bearer ', ''));

    if (!token) {
        // אם הטוקן לא קיים, נבצע הפניה לדף התחברות או נשלח תגובה של טוקן חסר
        if (req.cookies.token) {
            return res.redirect('/login?message=InvalidToken');
        } else {
            return res.status(403).json({ message: 'No token provided.' });
        }
    }

    // וודא את הטוקן
    jwt.verify(token, config.secret_key.key, (err, decoded) => {
        if (err) {
            return res.status(500).json({ auth: false, message: 'Failed to authenticate token.' });
        }

        // בדוק אם לטוקן יש שדה 'exp' (תאריך פקיעה)
        if (!decoded.exp) {
            return res.status(500).json({ auth: false, message: 'Token does not have an expiration date.' });
        }

        // אם הכל תקין, שמור את הנתונים לבקשה
        req.user = decoded;
        next();
    });
}

module.exports = verifyToken;
