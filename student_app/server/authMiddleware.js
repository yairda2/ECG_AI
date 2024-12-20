const jwt = require('jsonwebtoken');
const config = require('../config/config');
const url = require('url');

function verifyToken(req, res, next) {
    const token = req.cookies.token || (req.headers['authorization'] && req.headers['authorization'].replace('Bearer ', ''));

    if (!token) {
        const currentUrl = encodeURIComponent(req.originalUrl);
        return res.redirect(`/login?message=TokenNotFound&redirectUrl=${currentUrl}`);
    }

    jwt.verify(token, config.secret_key.key, (err, decoded) => {
        if (err) {
            const currentUrl = encodeURIComponent(req.originalUrl);

            if (err.name === 'TokenExpiredError') {
                return res.redirect(`/login?message=TokenExpired&redirectUrl=${currentUrl}`);
            }

            return res.redirect(`/login?message=InvalidToken&redirectUrl=${currentUrl}`);
        }

        if (!decoded.exp) {
            return res.redirect(`/login?message=InvalidToken&redirectUrl=${currentUrl}`);
        }

        req.user = decoded;
        next();
    });
}

module.exports = verifyToken;
