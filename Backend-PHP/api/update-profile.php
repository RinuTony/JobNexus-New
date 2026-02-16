<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);

require_once __DIR__ . '/../config/database.php';

header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Authorization");

if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    http_response_code(200);
    exit();
}

$input = json_decode(file_get_contents('php://input'), true);
$userId = $input['userId'] ?? 0;
$userRole = $input['role'] ?? null;

if (!$userId) {
    echo json_encode(['success' => false, 'message' => 'User ID required']);
    exit();
}

try {
    // âœ… Use Database class instead of creating own PDO
    $database = new Database();
    $db = $database->getConnection();
    
    // Resolve role from DB if not provided by client
    if (!$userRole) {
        $roleStmt = $db->prepare("SELECT role FROM users WHERE id = :user_id");
        $roleStmt->execute([':user_id' => $userId]);
        $userRole = $roleStmt->fetchColumn();
    }

    // Start transaction
    $db->beginTransaction();
    
    // Update common profile
    $stmt = $db->prepare("
        INSERT INTO profiles (user_id, first_name, last_name, phone) 
        VALUES (:user_id, :first_name, :last_name, :phone)
        ON DUPLICATE KEY UPDATE 
        first_name = VALUES(first_name),
        last_name = VALUES(last_name),
        phone = VALUES(phone)
    ");
    
    $stmt->execute([
        ':user_id' => $userId,
        ':first_name' => $input['firstName'] ?? '',
        ':last_name' => $input['lastName'] ?? '',
        ':phone' => $input['phone'] ?? ''
    ]);
    
    switch ($userRole) {
        case 'candidate':
            $skillsInput = $input['skills'] ?? [];
            $skillsValue = is_array($skillsInput) ? json_encode($skillsInput) : (string)$skillsInput;

            $stmt = $db->prepare("
                INSERT INTO candidate_profiles (
                    user_id, skills, preferred_location, salary_expectation, experience_years, current_company
                ) VALUES (
                    :user_id, :skills, :preferred_location, :salary_expectation, :experience_years, :current_company
                )
                ON DUPLICATE KEY UPDATE
                    skills = VALUES(skills),
                    preferred_location = VALUES(preferred_location),
                    salary_expectation = VALUES(salary_expectation),
                    experience_years = VALUES(experience_years),
                    current_company = VALUES(current_company)
            ");
            $stmt->execute([
                ':user_id' => $userId,
                ':skills' => $skillsValue,
                ':preferred_location' => $input['preferredLocation'] ?? '',
                ':salary_expectation' => ($input['salaryExpectation'] ?? '') === '' ? null : $input['salaryExpectation'],
                ':experience_years' => ($input['experienceYears'] ?? '') === '' ? null : $input['experienceYears'],
                ':current_company' => $input['currentCompany'] ?? ''
            ]);
            break;
        case 'recruiter':
            $stmt = $db->prepare("
                INSERT INTO recruiter_profiles (
                    user_id, company_name, company_size, industry, website
                ) VALUES (
                    :user_id, :company_name, :company_size, :industry, :website
                )
                ON DUPLICATE KEY UPDATE
                    company_name = VALUES(company_name),
                    company_size = VALUES(company_size),
                    industry = VALUES(industry),
                    website = VALUES(website)
            ");
            $stmt->execute([
                ':user_id' => $userId,
                ':company_name' => $input['companyName'] ?? '',
                ':company_size' => $input['companySize'] ?? '',
                ':industry' => $input['industry'] ?? '',
                ':website' => $input['website'] ?? ''
            ]);
            break;
        case 'admin':
            $stmt = $db->prepare("
                INSERT INTO admin_profiles (
                    user_id, college_name, department, position, student_count
                ) VALUES (
                    :user_id, :college_name, :department, :position, :student_count
                )
                ON DUPLICATE KEY UPDATE
                    college_name = VALUES(college_name),
                    department = VALUES(department),
                    position = VALUES(position),
                    student_count = VALUES(student_count)
            ");
            $stmt->execute([
                ':user_id' => $userId,
                ':college_name' => $input['collegeName'] ?? '',
                ':department' => $input['department'] ?? '',
                ':position' => $input['position'] ?? '',
                ':student_count' => ($input['studentCount'] ?? '') === '' ? null : $input['studentCount']
            ]);
            break;
    }

    // Optional password change through security section
    $newPassword = trim($input['newPassword'] ?? '');
    $currentPassword = trim($input['currentPassword'] ?? '');
    if ($newPassword !== '') {
        if ($currentPassword === '') {
            throw new Exception('Current password is required to set a new password');
        }
        $pwdStmt = $db->prepare("SELECT password FROM users WHERE id = :user_id");
        $pwdStmt->execute([':user_id' => $userId]);
        $storedPassword = $pwdStmt->fetchColumn();

        if ($storedPassword === false) {
            throw new Exception('User not found');
        }
        if ($storedPassword !== $currentPassword) {
            throw new Exception('Current password is incorrect');
        }

        $updatePwdStmt = $db->prepare("UPDATE users SET password = :new_password WHERE id = :user_id");
        $updatePwdStmt->execute([
            ':new_password' => $newPassword,
            ':user_id' => $userId
        ]);
    }
    
    // Commit transaction
    $db->commit();
    
    echo json_encode([
        'success' => true, 
        'message' => 'Profile updated successfully'
    ]);
    
} catch (Exception $e) {
    // Rollback on error
    if (isset($db) && $db->inTransaction()) {
        $db->rollBack();
    }
    
    http_response_code(500);
    echo json_encode([
        'success' => false, 
        'message' => $e->getMessage() ?: 'Profile update failed',
        'error' => $e->getMessage()
    ]);
}
?>
