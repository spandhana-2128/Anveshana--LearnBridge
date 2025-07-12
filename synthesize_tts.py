import argparse
import json
import torch
import numpy as np
from scipy.io.wavfile import write

class Synthesizer:
    def __init__(self, model_path, config_path):
        # Load model configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        # Load the model checkpoint
        checkpoint = torch.load(model_path, map_location='cpu')
        
        # Initialize the model and load parameters
        self.model = self.load_model_from_checkpoint(checkpoint)
        self.model.eval()

    def load_model_from_checkpoint(self, checkpoint):
        from TTS.models import FastPitch  # Replace with actual model class if different
        model = FastPitch.from_config_dict(self.config)
        model.load_state_dict(checkpoint['state_dict'])
        return model

    def tts(self, text):
        # Convert text to sequences
        sequences = self.text_to_sequence(text)
        with torch.no_grad():
            wavs = self.model.generate_spectrogram(sequences)
        return wavs

    def text_to_sequence(self, text):
        # Convert text to a sequence of integers (example)
        return [ord(c) for c in text]

    @property
    def sample_rate(self):
        return self.config.get('audio', {}).get('sample_rate', 22050)

def synthesize_text(model_path, config_path, text, output_path):
    synthesizer = Synthesizer(model_path, config_path)
    wavs = synthesizer.tts(text)
    write(output_path, synthesizer.sample_rate, np.asarray(wavs))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Synthesize speech from text using a TTS model.")
    parser.add_argument("--text", type=str, required=True, help="Text to synthesize.")
    parser.add_argument("--out_path", type=str, required=True, help="Output path for the .wav file.")
    parser.add_argument("--model_path", type=str, required=True, help="Path to the TTS model checkpoint.")
    parser.add_argument("--config_path", type=str, required=True, help="Path to the TTS model config file.")
    args = parser.parse_args()

    print(f"Text to synthesize: {args.text}")
    print(f"Output path: {args.out_path}")
    print(f"Model path: {args.model_path}")
    print(f"Config path: {args.config_path}")

    try:
        synthesize_text(args.model_path, args.config_path, args.text, args.out_path)
        print(f"Synthesis complete! Audio saved to {args.out_path}")
    except Exception as e:
        print(f"Error during synthesis: {str(e)}")
        exit(1)
