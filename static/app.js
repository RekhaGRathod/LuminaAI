// DOM Elements
const subjectCards = document.querySelectorAll('.subject-card');
const backButtons = document.querySelectorAll('.back-btn');
const loadMoreQuestionsBtn = document.getElementById('load-more-questions');
const loadMoreCustomQuestionsBtn = document.getElementById('load-more-custom-questions');
const generateCustomQuestionsBtn = document.getElementById('generate-custom-questions');
const submitDoubtBtn = document.getElementById('submit-doubt');
const loadingOverlay = document.getElementById('loading-overlay');

// State management
let currentSubject = '';
let currentChapter = '';
let currentTopic = '';
let currentCustomTopic = '';
let questionOffset = 0;
let customQuestionOffset = 0;
let questionsHistory = new Set(); // Track previously shown questions

// Navigation system
function navigateTo(targetScreen) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(targetScreen).classList.add('active');
}

// Event Listeners
subjectCards.forEach(card => {
    card.addEventListener('click', function() {
        currentSubject = this.getAttribute('data-subject');
        document.getElementById('subject-title').textContent = capitalizeFirstLetter(currentSubject) + ' Chapters';
        loadChapters(currentSubject);
        navigateTo('chapters-screen');
    });
});

backButtons.forEach(button => {
    button.addEventListener('click', function() {
        // Reset appropriate offsets based on which screen we're returning to
        const targetScreen = this.getAttribute('data-target');
        if (targetScreen === 'topics-screen') {
            questionOffset = 0;
        } else if (targetScreen === 'home-screen') {
            currentSubject = '';
            currentChapter = '';
            currentTopic = '';
        }
        navigateTo(targetScreen);
    });
});

loadMoreQuestionsBtn.addEventListener('click', function() {
    // Load next batch of questions
    questionOffset += 5;
    loadQuestions(currentSubject, currentChapter, currentTopic, questionOffset);
});

loadMoreCustomQuestionsBtn.addEventListener('click', function() {
    customQuestionOffset += 5;
    loadCustomQuestions(currentCustomTopic, customQuestionOffset);
});

generateCustomQuestionsBtn.addEventListener('click', function() {
    const customTopic = document.getElementById('custom-question-input').value.trim();
    if (customTopic) {
        currentCustomTopic = customTopic;
        customQuestionOffset = 0;
        document.querySelector('#custom-topic-display span').textContent = customTopic;
        loadCustomQuestions(customTopic, 0);
        navigateTo('custom-questions-screen');
    } else {
        alert('Please enter a topic to generate questions for.');
    }
});

submitDoubtBtn.addEventListener('click', function() {
    const doubt = document.getElementById('doubt-input').value.trim();
    if (doubt) {
        showLoading();
        askDoubt(doubt);
    } else {
        alert('Please enter your doubt first.');
    }
});

// API Calls
function loadChapters(subject) {
    showLoading();
    
    fetch('/api/chapters', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ subject: subject })
    })
    .then(response => response.json())
    .then(data => {
        renderChapters(data.chapters);
        hideLoading();
    })
    .catch(error => {
        console.error('Error loading chapters:', error);
        hideLoading();
        alert('Failed to load chapters. Please try again.');
    });
}

function loadTopics(subject, chapter) {
    showLoading();
    
    fetch('/api/topics', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            subject: subject,
            chapter: chapter
        })
    })
    .then(response => response.json())
    .then(data => {
        renderTopics(data.topics);
        hideLoading();
    })
    .catch(error => {
        console.error('Error loading topics:', error);
        hideLoading();
        alert('Failed to load topics. Please try again.');
    });
}

function loadQuestions(subject, chapter, topic, offset = 0) {
    showLoading();
    
    fetch('/api/questions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            subject: subject,
            chapter: chapter,
            topic: topic,
            offset: offset,
            history: Array.from(questionsHistory)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (offset === 0) {
            // Clear existing questions if this is the first batch
            document.getElementById('questions-list').innerHTML = '';
        }
        renderQuestions(data.questions, offset === 0);
        hideLoading();
        
        // Update load more button visibility
        loadMoreQuestionsBtn.style.display = data.hasMore ? 'block' : 'none';
    })
    .catch(error => {
        console.error('Error loading questions:', error);
        hideLoading();
        alert('Failed to load questions. Please try again.');
    });
}

function loadCustomQuestions(topic, offset = 0) {
    showLoading();
    
    fetch('/api/custom-questions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            topic: topic,
            offset: offset,
            history: Array.from(questionsHistory)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (offset === 0) {
            // Clear existing questions for first batch
            document.getElementById('custom-questions-list').innerHTML = '';
        }
        renderCustomQuestions(data.questions);
        hideLoading();
        
        // Update load more button visibility
        loadMoreCustomQuestionsBtn.style.display = data.hasMore ? 'block' : 'none';
    })
    .catch(error => {
        console.error('Error loading custom questions:', error);
        hideLoading();
        alert('Failed to load questions. Please try again.');
    });
}

function loadSolution(questionId) {
    showLoading();
    
    fetch('/api/solution', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ questionId: questionId })
    })
    .then(response => response.json())
    .then(data => {
        renderSolution(data.question, data.solution);
        navigateTo('solution-screen');
        hideLoading();
    })
    .catch(error => {
        console.error('Error loading solution:', error);
        hideLoading();
        alert('Failed to load solution. Please try again.');
    });
}

function askDoubt(doubt) {
    // Get the current question text
    const questionText = document.getElementById('current-question').textContent;
    
    fetch('/api/ask-doubt', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            question: questionText,
            doubt: doubt
        })
    })
    .then(response => response.json())
    .then(data => {
        const doubtResponse = document.getElementById('doubt-response');
        doubtResponse.innerHTML = data.response;
        doubtResponse.style.display = 'block';
        hideLoading();
    })
    .catch(error => {
        console.error('Error submitting doubt:', error);
        hideLoading();
        alert('Failed to get a response. Please try again.');
    });
}

// DOM Rendering Functions
function renderChapters(chapters) {
    const chaptersContainer = document.getElementById('chapters-list');
    chaptersContainer.innerHTML = '';
    
    chapters.forEach((chapter, index) => {
        const chapterCard = document.createElement('div');
        chapterCard.classList.add('card', 'chapter-card');
        chapterCard.innerHTML = `
            <h3>Chapter ${index + 1}: ${chapter.title}</h3>
            <p>${chapter.description}</p>
        `;
        
        chapterCard.addEventListener('click', function() {
            currentChapter = chapter.id;
            document.getElementById('chapter-title').textContent = `${chapter.title} Topics`;
            loadTopics(currentSubject, chapter.id);
            navigateTo('topics-screen');
        });
        
        chaptersContainer.appendChild(chapterCard);
    });
}

function renderTopics(topics) {
    const topicsContainer = document.getElementById('topics-list');
    topicsContainer.innerHTML = '';
    
    topics.forEach((topic, index) => {
        const topicCard = document.createElement('div');
        topicCard.classList.add('card', 'topic-card');
        topicCard.innerHTML = `
            <h3>${topic.title}</h3>
            <p>${topic.description}</p>
        `;
        
        topicCard.addEventListener('click', function() {
            currentTopic = topic.id;
            document.getElementById('topic-title').textContent = `${topic.title} - Practice Questions`;
            questionOffset = 0;
            loadQuestions(currentSubject, currentChapter, topic.id);
            navigateTo('questions-screen');
        });
        
        topicsContainer.appendChild(topicCard);
    });
}

function renderQuestions(questions, clearHistory = false) {
    const questionsContainer = document.getElementById('questions-list');
    
    if (clearHistory) {
        questionsHistory.clear();
    }
    
    questions.forEach(question => {
        // Add to history to avoid duplicates
        questionsHistory.add(question.id);
        
        const questionCard = document.createElement('div');
        questionCard.classList.add('question-card');
        
        // Create the HTML for the question
        let questionHTML = `
            <div class="question-text">${question.text}</div>
            <div class="question-options">
        `;
        
        // Add options
        question.options.forEach((option, index) => {
            questionHTML += `
                <div class="option" data-option="${index}">
                    ${String.fromCharCode(65 + index)}. ${option}
                </div>
            `;
        });
        
        // Close options div and add solution button
        questionHTML += `
            </div>
            <div class="question-actions">
                <button class="btn primary-btn view-solution-btn" data-question-id="${question.id}">View Solution</button>
            </div>
        `;
        
        questionCard.innerHTML = questionHTML;
        
        // Add event listeners for options
        const optionElements = questionCard.querySelectorAll('.option');
        optionElements.forEach(option => {
            option.addEventListener('click', function() {
                // Remove selected class from all options
                optionElements.forEach(opt => opt.classList.remove('selected'));
                // Add selected class to clicked option
                this.classList.add('selected');
                
                // Check if answer is correct
                const selectedIndex = parseInt(this.getAttribute('data-option'));
                if (selectedIndex === question.correctIndex) {
                    this.style.backgroundColor = '#d4edda'; // Green for correct
                } else {
                    this.style.backgroundColor = '#f8d7da'; // Red for incorrect
                    // Highlight correct answer
                    optionElements[question.correctIndex].style.backgroundColor = '#d4edda';
                }
            });
        });
        
        // Add event listener for solution button
        const solutionBtn = questionCard.querySelector('.view-solution-btn');
        solutionBtn.addEventListener('click', function() {
            const questionId = this.getAttribute('data-question-id');
            loadSolution(questionId);
        });
        
        questionsContainer.appendChild(questionCard);
    });
}

function renderCustomQuestions(questions) {
    const questionsContainer = document.getElementById('custom-questions-list');
    
    // Same as renderQuestions but for custom questions
    questions.forEach(question => {
        questionsHistory.add(question.id);
        
        const questionCard = document.createElement('div');
        questionCard.classList.add('question-card');
        
        let questionHTML = `
            <div class="question-text">${question.text}</div>
            <div class="question-options">
        `;
        
        question.options.forEach((option, index) => {
            questionHTML += `
                <div class="option" data-option="${index}">
                    ${String.fromCharCode(65 + index)}. ${option}
                </div>
            `;
        });
        
        questionHTML += `
            </div>
            <div class="question-actions">
                <button class="btn primary-btn view-solution-btn" data-question-id="${question.id}">View Solution</button>
            </div>
        `;
        
        questionCard.innerHTML = questionHTML;
        
        const optionElements = questionCard.querySelectorAll('.option');
        optionElements.forEach(option => {
            option.addEventListener('click', function() {
                optionElements.forEach(opt => opt.classList.remove('selected'));
                this.classList.add('selected');
                
                const selectedIndex = parseInt(this.getAttribute('data-option'));
                if (selectedIndex === question.correctIndex) {
                    this.style.backgroundColor = '#d4edda';
                } else {
                    this.style.backgroundColor = '#f8d7da';
                    optionElements[question.correctIndex].style.backgroundColor = '#d4edda';
                }
            });
        });
        
        const solutionBtn = questionCard.querySelector('.view-solution-btn');
        solutionBtn.addEventListener('click', function() {
            const questionId = this.getAttribute('data-question-id');
            loadSolution(questionId);
        });
        
        questionsContainer.appendChild(questionCard);
    });
}

function renderSolution(question, solution) {
    // Display the question
    document.getElementById('current-question').innerHTML = `
        <div class="question-text">${question.text}</div>
        <div class="question-options">
            ${question.options.map((option, index) => 
                `<div class="option ${index === question.correctIndex ? 'correct' : ''}">
                    ${String.fromCharCode(65 + index)}. ${option}
                    ${index === question.correctIndex ? ' <span class="correct-indicator">✓</span>' : ''}
                </div>`
            ).join('')}
        </div>
    `;
    
    // Display the solution steps
    const solutionStepsContainer = document.getElementById('solution-steps');
    solutionStepsContainer.innerHTML = '<h3>Step-by-Step Solution:</h3>';
    
    solution.steps.forEach((step, index) => {
        const stepElement = document.createElement('div');
        stepElement.classList.add('solution-step');
        stepElement.innerHTML = `
            <div class="step-title">Step ${index + 1}: ${step.title}</div>
            <div class="step-content">${step.content}</div>
        `;
        solutionStepsContainer.appendChild(stepElement);
    });
    
    // Clear previous doubt response and input
    document.getElementById('doubt-response').style.display = 'none';
    document.getElementById('doubt-input').value = '';
}

// Utility Functions
function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

function showLoading() {
    loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    loadingOverlay.style.display = 'none';
}

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    // Any initialization code goes here
    // For example, we could pre-fetch subject data
    
    // Add event delegation for dynamically created elements
    document.body.addEventListener('click', function(event) {
        // Handle dynamic elements if needed
    });
});