
from manim import *
from manim_editor import PresentationSectionType
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService
from manim_speech import install_speech
import numpy as np

# For code demonstrations if needed
try:
    from manim_code_blocks import Code
except ImportError:
    pass

# For neural network visualization if needed
try:
    from manim_neural_network import NeuralNetworkMobject
except ImportError:
    pass

# For data structure visualization if needed
try:
    from manim_data_structures import Array, LinkedList, Stack, Queue, BinaryTree
except ImportError:
    pass

# Install speech recognition for interactive elements
install_speech()

class IntroductiontoSecurityFundamentalsScene(VoiceoverScene):
    def construct(self):
        # Initialize the text-to-speech service
        self.set_speech_service(GTTSService())
        
        # Create presentation sections for manim-editor integration
        # This allows for easier editing and slide-based navigation
        
        # SECTION 1: Introduction
        with self.voiceover(f"Welcome to this lesson about Introduction to Security Fundamentals.") as tracker:
            self.next_section("Introduction", PresentationSectionType.NORMAL)
            title = Text("Introduction to Security Fundamentals", font_size=40)
            self.play(Write(title))
            self.wait(tracker.duration - 2)
            self.play(title.animate.to_edge(UP))
        
        # SECTION 2: Overview
        with self.voiceover(f"In this moderate video, we'll explore key concepts related to Introduction to Security Fundamentals.") as tracker:
            self.next_section("Overview", PresentationSectionType.NORMAL)
            intro_text = Text(f"This moderate video covers Introduction to Security Fundamentals", font_size=24)
            self.play(Write(intro_text))
            self.wait(tracker.duration - 2)
            self.play(FadeOut(intro_text))
        
        # SECTION 3: Main Content
        self.next_section("Main Content", PresentationSectionType.NORMAL)
        
        # Example visualization based on learning style
        if learning_style == "visual":
            # Visual-focused content with minimal text
            with self.voiceover("Let's visualize the key concepts with clear graphics.") as tracker:
                circle = Circle(radius=2, color=BLUE)
                self.play(Create(circle))
                self.wait(1)
                square = Square(side_length=3, color=GREEN)
                self.play(Transform(circle, square))
                self.wait(1)
        
        elif learning_style == "auditory":
            # Audio-focused content with narration cues
            with self.voiceover("I'll explain the concepts step by step. Listen carefully as each point builds on the previous one.") as tracker:
                steps = VGroup(
                    Text("Step 1: Foundation", font_size=28),
                    Text("Step 2: Application", font_size=28),
                    Text("Step 3: Advanced Concepts", font_size=28)
                ).arrange(DOWN, buff=0.8)
                
                for step in steps:
                    self.play(Write(step))
                    self.wait(2)
                self.play(FadeOut(steps))
        
        elif learning_style == "hands-on":
            # Code and practical examples for hands-on learners
            with self.voiceover("Let's look at some practical code examples that demonstrate these concepts.") as tracker:
                try:
                    code = Code(
                        code='''
def example_function():
    # This demonstrates Introduction to Security Fundamentals
    result = process_data()
    return analyze(result)
                        ''',
                        language="python",
                        font="Monospace",
                        font_size=24
                    )
                    self.play(Create(code))
                    self.wait(3)
                    self.play(FadeOut(code))
                except:
                    # Fallback if Code isn't available
                    code_text = Text("def example_function():\n    # Code example here", font_size=24)
                    self.play(Write(code_text))
                    self.wait(3)
                    self.play(FadeOut(code_text))
        
        # SECTION 4: Examples (could include data structures, algorithms, neural networks based on topic)
        self.next_section("Examples", PresentationSectionType.NORMAL)
        with self.voiceover(f"Here are some examples related to Introduction to Security Fundamentals.") as tracker:
            # Try to use topic-relevant visualizations using specialty packages
            if "data" in topic.lower() or "structure" in topic.lower():
                try:
                    # Use data structures visualization
                    array = Array([1, 2, 3, 4, 5])
                    self.play(Create(array))
                    self.wait(2)
                    self.play(FadeOut(array))
                except:
                    # Fallback
                    data_viz = Text("Data Structure Visualization", font_size=24)
                    self.play(Write(data_viz))
                    self.wait(2)
                    self.play(FadeOut(data_viz))
            
            elif "neural" in topic.lower() or "machine learning" in topic.lower() or "ai" in topic.lower():
                try:
                    # Neural network visualization
                    nn = NeuralNetworkMobject([3, 4, 2])
                    self.play(Create(nn))
                    self.wait(2)
                    self.play(FadeOut(nn))
                except:
                    # Fallback
                    nn_viz = Text("Neural Network Visualization", font_size=24)
                    self.play(Write(nn_viz))
                    self.wait(2)
                    self.play(FadeOut(nn_viz))
            
            else:
                # Generic visualization
                # Define bounds for LaTeX integration formula
                lower_bound = "a"  # Integration lower bound 
                upper_bound = "b"  # Integration upper bound
                # Construct the LaTeX formula string with explicit values to avoid undefined variable errors
                formula_text = r"f(x) = \int_ + lower_bound + r^ + upper_bound + r g(x) dx"
                formula = MathTex(formula_text)
                self.play(Write(formula))
                self.wait(2)
                self.play(FadeOut(formula))
        
        # SECTION 5: Summary
        self.next_section("Summary", PresentationSectionType.NORMAL)
        with self.voiceover("Let's summarize what we've learned about " + topic + ".") as tracker:
            conclusion = Text("Summary of key points", font_size=28)
            self.play(Write(conclusion))
            self.wait(tracker.duration - 1)
            
            # Final title with manim-editor section for easy ending
            self.next_section("Ending", PresentationSectionType.NORMAL)
            with self.voiceover("Thanks for watching this video on " + topic + ".") as tracker:
                final_title = Text("Thanks for watching!", font_size=36)
                self.play(ReplacementTransform(conclusion, final_title))
                self.wait(tracker.duration)
    