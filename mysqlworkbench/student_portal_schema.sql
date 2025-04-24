DROP DATABASE IF EXISTS student_portal;

CREATE DATABASE student_portal;

USE student_portal;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    grade VARCHAR(20) NOT NULL,
    student_id VARCHAR(20) UNIQUE,
    user_id INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create a session tracking table
CREATE TABLE IF NOT EXISTS active_sessions (
    connection_id INT PRIMARY KEY,
    user_id INT NOT NULL,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Create a view that joins with active sessions
CREATE OR REPLACE ALGORITHM=MERGE SQL SECURITY DEFINER VIEW current_user_data AS
SELECT s.* 
FROM students s
JOIN active_sessions a ON s.user_id = a.user_id
WHERE a.connection_id = CONNECTION_ID();

-- Procedure to set user context
DELIMITER //
CREATE PROCEDURE set_user_context(IN p_user_id INT)
BEGIN
    SET @current_user_id = p_user_id;
    
    -- Track active session
    INSERT INTO active_sessions (connection_id, user_id)
    VALUES (CONNECTION_ID(), p_user_id)
    ON DUPLICATE KEY UPDATE user_id = p_user_id, login_time = CURRENT_TIMESTAMP;
END //
DELIMITER ;

-- Procedure to clear user context
DELIMITER //
CREATE PROCEDURE clear_user_context()
BEGIN
    DELETE FROM active_sessions WHERE connection_id = CONNECTION_ID();
    SET @current_user_id = NULL;
END //
DELIMITER ;

-- Procedure to get current user's students
DELIMITER //
CREATE PROCEDURE get_my_students()
BEGIN
    SELECT * FROM current_user_data;
END //
DELIMITER ;

-- Cleanup procedure for old sessions
DELIMITER //
CREATE PROCEDURE cleanup_sessions()
BEGIN
    DELETE FROM active_sessions 
    WHERE login_time < DATE_SUB(NOW(), INTERVAL 8 HOUR);
END //
DELIMITER ;

-- Event to regularly clean up old sessions
CREATE EVENT IF NOT EXISTS session_cleanup
ON SCHEDULE EVERY 1 HOUR
DO CALL cleanup_sessions();

SELECT * FROM current_user_data;
select * from users;
select * from students;