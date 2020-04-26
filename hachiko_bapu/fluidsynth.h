void* new_fluid_settings();
void delete_fluid_settings(void* settings);

void* new_fluid_synth(void* settings);
void delete_fluid_synth(void* synth);

int fluid_settings_setstr(void* settings, char* name, char* str);
int fluid_settings_setnum(void* settings, char* name, double val);

int fluid_settings_setint(void* settings, char* name, int val);

int fluid_synth_sfload(void* synth, char* filename, int update_midi_presets);
int fluid_synth_sfunload(void* synth, int sfid, int update_midi_presets);

int fluid_synth_program_select(void* synth, int chan, int sfid, int bank, int preset);

int fluid_synth_noteon(void* synth, int chan, int key, int vel);
int fluid_synth_noteoff(void* synth, int chan, int key);

void fluid_synth_write_s16(void* synth, int len, void* lbuf, int loff, int lincr, void* rbuf, int roff, int rincl);

void* new_fluid_audio_driver(void* settings, void* synth);

void delete_fluid_audio_driver(void* driver);
