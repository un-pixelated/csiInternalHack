class MockAPI {
  constructor() {
    this.wordBank = [
      "apple",
      "logic",
      "memory",
      "system",
      "neural",
      "compute",
      "vector",
      "matrix",
      "binary",
      "cache",
      "thread",
      "kernel",
      "buffer",
      "pipeline",
      "latency",
      "runtime",
      "compile",
      "debug",
      "syntax",
      "parser",
      "lexer",
      "token",
      "stack",
      "heap",
      "queue",
      "graph",
      "tree",
      "node",
      "edge",
      "vertex",
      "algorithm",
      "function",
      "variable",
      "object",
      "array",
      "string",
    ];
  }

  async getNextWord(seenWords) {
    return new Promise((resolve) => {
      setTimeout(() => {
        const shouldRepeat = seenWords.length > 0 && Math.random() < 0.35;

        let word;
        if (shouldRepeat) {
          word = seenWords[Math.floor(Math.random() * seenWords.length)];
        } else {
          let attempts = 0;
          do {
            word =
              this.wordBank[Math.floor(Math.random() * this.wordBank.length)];
            attempts++;
          } while (seenWords.includes(word) && attempts < 50);
        }

        const difficulty = Math.random();
        const time_limit = 5.0 - difficulty * 3.0;

        resolve({
          word,
          difficulty: parseFloat(difficulty.toFixed(2)),
          time_limit: parseFloat(time_limit.toFixed(1)),
        });
      }, 100);
    });
  }

  async saveScore(score, mode) {
    return new Promise((resolve) => {
      setTimeout(() => {
        console.log("\n=== SCORE SAVED ===");
        console.log(`Score: ${score}`);
        console.log(`Mode: ${mode}`);
        resolve({ success: true });
      }, 100);
    });
  }
}

class GameEngine {
  constructor() {
    this.state = {
      authToken: null,
      gameState: "MENU",
      gameMode: "medium",
      currentScore: 0,
      lives: 3,
      seenWords: [],
      currentWordData: {
        word: "",
        difficulty: 0.5,
        time_limit: 0.0,
      },
      timerValue: 0.0,
    };

    this.api = new MockAPI();
    this.timerInterval = null;
    this.isProcessingAnswer = false;
  }

  async startGame() {
    if (this.state.gameState === "PLAYING") {
      console.log("Game already in progress!");
      return;
    }

    console.log("\n=== GAME STARTED ===");
    console.log(`Mode: ${this.state.gameMode}`);

    this.state.gameState = "PLAYING";
    this.state.currentScore = 0;
    this.state.lives = 3;
    this.state.seenWords = [];

    await this.fetchNextWord();
  }

  async fetchNextWord() {
    if (this.state.gameState !== "PLAYING") return;

    const wordData = await this.api.getNextWord(this.state.seenWords);

    this.state.currentWordData = wordData;
    this.state.timerValue = wordData.time_limit;

    console.log("\n--- NEW WORD ---");
    console.log(`Word: ${wordData.word}`);
    console.log(`Difficulty: ${wordData.difficulty}`);
    console.log(`Time Limit: ${wordData.time_limit}s`);
    console.log(
      `Score: ${this.state.currentScore} | Lives: ${this.state.lives}`,
    );

    this.startTimer();
  }

  startTimer() {
    this.stopTimer();

    const startTime = Date.now();
    const duration = this.state.timerValue * 1000;

    this.timerInterval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, duration - elapsed) / 1000;

      this.state.timerValue = parseFloat(remaining.toFixed(1));

      if (remaining <= 0) {
        this.handleTimerExpiry();
      }
    }, 100);
  }

  stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  handleTimerExpiry() {
    if (this.isProcessingAnswer) return;

    this.stopTimer();
    console.log("\n⏰ TIME'S UP!");
    this.handleWrongAnswer();
  }

  answerSeen() {
    if (this.state.gameState !== "PLAYING") {
      console.log("No game in progress. Call game.startGame() first.");
      return;
    }

    if (this.isProcessingAnswer) {
      console.log("Already processing an answer...");
      return;
    }

    this.isProcessingAnswer = true;
    this.stopTimer();

    const isCorrect = this.state.seenWords.includes(
      this.state.currentWordData.word,
    );

    console.log(`\nYou answered: SEEN`);

    if (isCorrect) {
      this.handleCorrectAnswer();
    } else {
      this.handleWrongAnswer();
    }
  }

  answerNew() {
    if (this.state.gameState !== "PLAYING") {
      console.log("No game in progress. Call game.startGame() first.");
      return;
    }

    if (this.isProcessingAnswer) {
      console.log("Already processing an answer...");
      return;
    }

    this.isProcessingAnswer = true;
    this.stopTimer();

    const isCorrect = !this.state.seenWords.includes(
      this.state.currentWordData.word,
    );

    console.log(`\nYou answered: NEW`);

    if (isCorrect) {
      this.handleCorrectAnswer();
    } else {
      this.handleWrongAnswer();
    }
  }

  handleCorrectAnswer() {
    console.log("✓ CORRECT!");
    this.state.currentScore++;
    console.log(`Score: ${this.state.currentScore}`);

    this.state.seenWords.push(this.state.currentWordData.word);

    this.isProcessingAnswer = false;

    setTimeout(() => {
      this.fetchNextWord();
    }, 500);
  }

  handleWrongAnswer() {
    console.log("✗ WRONG!");
    this.state.lives--;
    console.log(`Lives remaining: ${this.state.lives}`);

    this.state.seenWords.push(this.state.currentWordData.word);

    if (this.state.lives <= 0) {
      this.gameOver();
    } else {
      this.isProcessingAnswer = false;
      setTimeout(() => {
        this.fetchNextWord();
      }, 500);
    }
  }

  async gameOver() {
    this.stopTimer();
    this.state.gameState = "GAME_OVER";

    console.log("\n=== GAME OVER ===");
    console.log(`Final Score: ${this.state.currentScore}`);
    console.log(`Mode: ${this.state.gameMode}`);

    await this.api.saveScore(this.state.currentScore, this.state.gameMode);

    console.log("\nStart a new game with: game.startGame()");

    this.isProcessingAnswer = false;
  }

  getState() {
    return { ...this.state };
  }

  setMode(mode) {
    if (!["easy", "medium", "hard"].includes(mode)) {
      console.log("Invalid mode. Use: 'easy', 'medium', or 'hard'");
      return;
    }

    if (this.state.gameState === "PLAYING") {
      console.log("Cannot change mode during active game.");
      return;
    }

    this.state.gameMode = mode;
    console.log(`Mode set to: ${mode}`);
  }
}

const game = new GameEngine();

console.log("=== VERBAL MEMORY GAME ===");
console.log("Commands:");
console.log("  game.startGame()    - Start a new game");
console.log("  game.answerSeen()   - Answer 'SEEN'");
console.log("  game.answerNew()    - Answer 'NEW'");
console.log("  game.setMode(mode)  - Set difficulty ('easy'/'medium'/'hard')");
console.log("  game.getState()     - View current state");
console.log("\nReady to play!");

window.game = game;
