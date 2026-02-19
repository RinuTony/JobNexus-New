<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

header("Content-Type: application/json");

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

require_once __DIR__ . '/../config/database.php';

function ensureAcceptingApplicationsColumn(PDO $db): void {
    try {
        $db->exec("ALTER TABLE jobs ADD COLUMN accepting_applications TINYINT(1) NOT NULL DEFAULT 1");
    } catch (PDOException $e) {
        $message = strtolower($e->getMessage());
        if (strpos($message, 'duplicate column') === false && strpos($message, '1060') === false) {
            throw $e;
        }
    }
}

function ensureRequiredSkillsColumn(PDO $db): void {
    try {
        $db->exec("ALTER TABLE jobs ADD COLUMN required_skills TEXT NULL");
    } catch (PDOException $e) {
        $message = strtolower($e->getMessage());
        if (strpos($message, 'duplicate column') === false && strpos($message, '1060') === false) {
            throw $e;
        }
    }
}

$input = json_decode(file_get_contents("php://input"), true);

if (
    !$input ||
    empty($input['title']) ||
    empty($input['description']) ||
    empty($input['recruiter_id']) ||
    empty($input['required_skills'])
) {
    echo json_encode([
        "success" => false,
        "message" => "Missing required fields"
    ]);
    exit();
}

$title = trim($input['title']);
$description = trim($input['description']);
$requiredSkills = trim((string)($input['required_skills'] ?? ''));
$recruiterId = (int)$input['recruiter_id'];

try {
    $database = new Database();
    $db = $database->getConnection();
    ensureAcceptingApplicationsColumn($db);
    ensureRequiredSkillsColumn($db);

    $stmt = $db->prepare("
        INSERT INTO jobs (title, description, required_skills, recruiter_id, accepting_applications, created_at)
        VALUES (:title, :description, :required_skills, :recruiter_id, 1, NOW())
    ");

    $stmt->execute([
        ":title" => $title,
        ":description" => $description,
        ":required_skills" => $requiredSkills,
        ":recruiter_id" => $recruiterId
    ]);

    echo json_encode([
        "success" => true,
        "message" => "Job posted successfully",
        "job_id" => $db->lastInsertId()
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode([
        "success" => false,
        "message" => "Failed to post job",
        "error" => $e->getMessage()
    ]);
}
?>
