#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Defines autosub's command line functionality.
"""
# pylint: disable=too-many-lines

from __future__ import absolute_import, print_function, unicode_literals

# Import built-in modules
import os

# Import third-party modules
import pysubs2
import auditok
import googletrans
import langcodes

# Any changes to the path and your own modules
from autosub import constants
from autosub import core
from autosub import ffmpeg_utils
from autosub import sub_utils
from autosub import lang_code_utils


def list_args(args):
    """
    Check if there's any list args.
    """
    if args.list_formats:
        print("List of output formats:\n")
        print("{column_1}{column_2}".format(
            column_1="Format".ljust(16),
            column_2="Description"))
        for subtitles_format, format_description in sorted(constants.OUTPUT_FORMAT.items()):
            print("{column_1}{column_2}".format(
                column_1=subtitles_format.ljust(16),
                column_2=format_description))
        print("\nList of input formats:\n")
        print("{column_1}{column_2}".format(
            column_1="Format".ljust(16),
            column_2="Description"))
        for subtitles_format, format_description in sorted(constants.INPUT_FORMAT.items()):
            print("{column_1}{column_2}".format(
                column_1=subtitles_format.ljust(16),
                column_2=format_description))
        return True

    if args.list_speech_codes:
        if args.list_speech_codes == ' ':
            print("List of all lang codes for speech-to-text:\n")
            print("{column_1}{column_2}".format(
                column_1="Lang code".ljust(16),
                column_2="Description"))
            for code, language in sorted(constants.SPEECH_TO_TEXT_LANGUAGE_CODES.items()):
                print("{column_1}{column_2}".format(
                    column_1=code.ljust(16),
                    column_2=language))
        else:
            print("Match speech lang codes.")
            lang_code_utils.match_print(
                dsr_lang=args.list_speech_codes,
                match_list=list(constants.SPEECH_TO_TEXT_LANGUAGE_CODES.keys()),
                min_score=args.min_score)
        return True

    if args.list_translation_codes:
        if args.list_translation_codes == ' ':
            print("List of all lang codes for translation:\n")
            print("{column_1}{column_2}".format(
                column_1="Lang code".ljust(16),
                column_2="Description"))
            for code, language in sorted(constants.TRANSLATION_LANGUAGE_CODES.items()):
                print("{column_1}{column_2}".format(
                    column_1=code.ljust(16),
                    column_2=language))
        else:
            print("Match translation lang codes.")
            lang_code_utils.match_print(
                dsr_lang=args.list_translation_codes,
                match_list=list(constants.TRANSLATION_LANGUAGE_CODES.keys()),
                min_score=args.min_score)
        return True

    return False


def validate_io(  # pylint: disable=too-many-branches, too-many-statements
        args,
        styles_list):
    """
    Give args and choose workflow depends on the io options.
    """
    if not args.input or not os.path.isfile(args.input):
        raise core.PrintAndStopException(
            "Error: arg of \"-i\"/\"--input\": \"{path}\" isn't valid. "
            "You need to give a valid path.".format(path=args.input))

    if args.styles:  # pylint: disable=too-many-nested-blocks
        if not os.path.isfile(args.styles):
            raise core.PrintAndStopException(
                "Error: arg of \"-sty\"/\"--styles\": \"{path}\" isn't valid. "
                "You need to give a valid path.".format(path=args.styles))

        if args.styles_name:
            if len(args.styles_name) > 2:
                raise core.PrintAndStopException(
                    "Error: Too many \"-sn\"/\"--styles-name\" arguments."
                )
            else:
                style_obj = pysubs2.SSAFile.load(args.styles)
                ass_styles = style_obj.styles.get(args.styles_name[0])
                if ass_styles:
                    styles_dict = {args.styles_name[0]: ass_styles}
                    if len(args.styles_name) == 2:
                        ass_styles = style_obj.styles.get(args.styles_name[1])
                        if ass_styles:
                            styles_dict[args.styles_name[1]] = ass_styles
                        else:
                            raise core.PrintAndStopException(
                                "Error: \"-sn\"/\"--styles-name\" "
                                "arguments aren't in \"{path}\".".format(path=args.styles)
                            )
                    for item in styles_dict.items():
                        styles_list.append(item[0])
                        styles_list.append(item[1])
                else:
                    raise core.PrintAndStopException(
                        "Error: \"-sn\"/\"--styles-name\" "
                        "arguments aren't in \"{path}\".".format(path=args.styles)
                    )

    if args.ext_regions and not os.path.isfile(args.ext_regions):
        raise core.PrintAndStopException(
            "Error: arg of \"-er\"/\"--ext-regions\": \"{path}\" isn't valid. "
            "You need to give a valid path.".format(path=args.ext_regions))

    args.input = args.input.replace("\\", "/")

    input_name = os.path.splitext(args.input)
    input_ext = input_name[-1]
    input_fmt = input_ext.strip('.')
    input_path = input_name[0]

    is_ass_input = input_fmt in constants.INPUT_FORMAT

    if not args.output:
        args.output = input_path
        # get output name from input path
        if not args.format:
            # get format from default
            if is_ass_input:
                args.format = input_fmt
                print("No output format specified. "
                      "Use input format \"{fmt}\" "
                      "for output.".format(fmt=input_fmt))
            else:
                args.format = constants.DEFAULT_SUBTITLES_FORMAT

    elif os.path.isdir(args.output):
        # windows path issues
        args.output = args.output.replace("\\", "/")
        args.output = args.output.rstrip('/') + \
            '/' + os.path.basename(args.input).rstrip(input_ext)
        # output = path + basename of input without extension
        print("Your output is a directory not a file path. "
              "Now file path set to {new}".format(new=args.output))
        if not args.format:
            # get format from default
            if is_ass_input:
                args.format = input_fmt
                print("No output format specified. "
                      "Use input format for output.")
            else:
                args.format = constants.DEFAULT_SUBTITLES_FORMAT
    else:
        args.output = args.output.replace("\\", "/")
        if not args.format:
            # get format from output
            args.format = input_ext.strip('.')
            # format = output name extension without dot
        args.output = input_path
        # output = output name without extension

    if args.format not in constants.OUTPUT_FORMAT:
        raise core.PrintAndStopException(
            "Error: Output subtitles format \"{fmt}\" not supported. "
            "Run with \"-lf\"/\"--list-formats\" to see all supported formats.\n"
            "Or use ffmpeg or SubtitleEdit to convert the formats.".format(fmt=args.format)
        )

    args.output_files = set(args.output_files)
    if "all" in args.output_files:
        args.output_files = constants.DEFAULT_MODE_SET
    else:
        if not is_ass_input:
            args.output_files = args.output_files & \
                                constants.DEFAULT_MODE_SET
            if not args.output_files:
                raise core.PrintAndStopException(
                    "Error: No valid \"-of\"/\"--output-files\" arguments."
                )
        else:
            args.output_files = args.output_files & \
                                constants.DEFAULT_SUB_MODE_SET
            if not args.output_files:
                raise core.PrintAndStopException(
                    "Error: No valid \"-of\"/\"--output-files\" arguments."
                )

    if args.best_match:
        args.best_match = {k.lower() for k in args.best_match}
        if 'all' in args.best_match:
            args.best_match = constants.DEFAULT_LANG_MODE_SET
        else:
            args.best_match = \
                args.best_match & constants.DEFAULT_LANG_MODE_SET

    if is_ass_input:
        print("Input is a subtitles file.")
        return 1

    return 0


def validate_aovp_args(args):  # pylint: disable=too-many-branches, too-many-return-statements, too-many-statements
    """
    Check that the commandline arguments passed to autosub are valid
    for audio or video processing.
    """
    if args.sleep_seconds < 0 or args.lines_per_trans < 0:
        raise core.PrintAndStopException(
            "Error: \"-slp\"/\"--sleep-seconds\" arg is illegal. "
        )

    if args.speech_language:  # pylint: disable=too-many-nested-blocks
        if not args.gspeechv2:
            args.speech_language = args.speech_language.lower()
            if args.speech_language \
                    not in constants.SPEECH_TO_TEXT_LANGUAGE_CODES:
                print(
                    "Warning: Speech language \"{src}\" not recommended. "
                    "Run with \"-lsc\"/\"--list-speech-codes\" "
                    "to see all supported languages.".format(src=args.speech_language)
                )
                if args.best_match and 's' in args.best_match:
                    best_result = lang_code_utils.match_print(
                        dsr_lang=args.speech_language,
                        match_list=list(constants.SPEECH_TO_TEXT_LANGUAGE_CODES.keys()),
                        min_score=args.min_score)
                    if best_result:
                        print("Use langcodes to standardize the result.")
                        args.speech_language = langcodes.standardize_tag(best_result[0])
                        print("Use {lang_code} instead.".format(lang_code=args.speech_language))
                    else:
                        print(
                            "Match failed. Still using {lang_code}".format(
                                lang_code=args.speech_language))

            if args.min_confidence < 0.0 or args.min_confidence > 1.0:
                raise core.PrintAndStopException(
                    "Error: min_confidence's value isn't legal."
                )

        if args.dst_language is None:
            print(
                "Destination language not provided. "
                "Only performing speech recognition."
            )

        else:
            if args.src_language is None:
                print(
                    "Source language not provided. "
                    "Use Speech language instead."
                )
                args.src_language = args.speech_language

            is_src_matched = False
            is_dst_matched = False

            for key in googletrans.constants.LANGUAGES:
                if args.src_language.lower() == key.lower():
                    args.src_language = key
                    is_src_matched = True
                if args.dst_language.lower() == key.lower():
                    args.dst_language = key
                    is_dst_matched = True

            if not is_src_matched:
                if not args.gtransv2:
                    if args.best_match and 'src' in args.best_match:
                        print(
                            "Warning: Source language \"{src}\" not supported. "
                            "Run with \"-lsc\"/\"--list-translation-codes\" "
                            "to see all supported languages.".format(src=args.src_language)
                        )
                        best_result = lang_code_utils.match_print(
                            dsr_lang=args.src_language,
                            match_list=list(googletrans.constants.LANGUAGES.keys()),
                            min_score=args.min_score)
                        if best_result:
                            print("Use {lang_code} instead.".format(lang_code=best_result[0]))
                            args.src_language = best_result[0]
                        else:
                            raise core.PrintAndStopException(
                                "Match failed. Still using {lang_code}. "
                                "Program stopped".format(
                                    lang_code=args.src_language))

                    else:
                        raise core.PrintAndStopException(
                            "Error: Source language \"{src}\" not supported. "
                            "Run with \"-lsc\"/\"--list-translation-codes\" "
                            "to see all supported languages. "
                            "Or use \"-bm\"/\"--best-match\" to get a best match".format(
                                src=args.speech_language)
                        )

            if not is_dst_matched:
                if not args.gtransv2:
                    if args.best_match and 'd' in args.best_match:
                        print(
                            "Warning: Destination language \"{dst}\" not supported. "
                            "Run with \"-lsc\"/\"--list-translation-codes\" "
                            "to see all supported languages.".format(dst=args.dst_language)
                        )
                        best_result = lang_code_utils.match_print(
                            dsr_lang=args.dst_language,
                            match_list=list(googletrans.constants.LANGUAGES.keys()),
                            min_score=args.min_score)
                        if best_result:
                            print("Use {lang_code} instead.".format(lang_code=best_result[0]))
                            args.dst_language = best_result[0]
                        else:
                            raise core.PrintAndStopException(
                                "Match failed. Still using {lang_code}. "
                                "Program stopped".format(
                                    lang_code=args.dst_language))

                    else:
                        raise core.PrintAndStopException(
                            "Error: Destination language \"{dst}\" not supported. "
                            "Run with \"-lsc\"/\"--list-translation-codes\" "
                            "to see all supported languages. "
                            "Or use \"-bm\"/\"--best-match\" to get a best match".format(
                                dst=args.speech_language)
                        )

        if args.dst_language == args.speech_language\
                or args.src_language == args.dst_language:
            print(
                "Speech language is the same as the Destination language. "
                "Only performing speech recognition."
            )
            args.dst_language = None
            args.src_language = None

    else:
        if args.ext_regions:
            raise core.PrintAndStopException(
                "You've already input times. "
                "No works done."
            )

        else:
            print(
                "Speech language not provided. "
                "Only performing speech regions detection."
            )

    if args.styles == ' ':
        # when args.styles is used but without option
        # its value is ' '
        if not args.ext_regions:
            raise core.PrintAndStopException(
                "Error: External speech regions file not provided."
            )
        else:
            args.styles = args.ext_regions


def validate_sp_args(args):  # pylint: disable=too-many-branches,too-many-return-statements, too-many-statements
    """
    Check that the commandline arguments passed to autosub are valid
    for subtitles processing.
    """
    if args.src_language:
        if args.dst_language is None:
            raise core.PrintAndStopException(
                "Error: Destination language not provided. "
            )

        is_src_matched = False
        is_dst_matched = False

        for key in googletrans.constants.LANGUAGES:
            if args.src_language.lower() == key.lower():
                args.src_language = key
                is_src_matched = True
            if args.dst_language.lower() == key.lower():
                args.dst_language = key
                is_dst_matched = True

        if not is_src_matched:
            if not args.gtransv2:
                if args.best_match and 'src' in args.best_match:
                    print(
                        "Warning: Source language \"{src}\" not supported. "
                        "Run with \"-lsc\"/\"--list-translation-codes\" "
                        "to see all supported languages.".format(src=args.src_language)
                    )
                    best_result = lang_code_utils.match_print(
                        dsr_lang=args.src_language,
                        match_list=list(googletrans.constants.LANGUAGES.keys()),
                        min_score=args.min_score)
                    if best_result:
                        print("Use {lang_code} instead.".format(lang_code=best_result[0]))
                        args.src_language = best_result[0]
                    else:
                        raise core.PrintAndStopException(
                            "Match failed. Still using {lang_code}. "
                            "Program stopped".format(
                                lang_code=args.src_language))

                else:
                    raise core.PrintAndStopException(
                        "Error: Source language \"{src}\" not supported. "
                        "Run with \"-lsc\"/\"--list-translation-codes\" "
                        "to see all supported languages. "
                        "Or use \"-bm\"/\"--best-match\" to get a best match".format(
                            src=args.src_language)
                    )

        if not is_dst_matched:
            if not args.gtransv2:
                if args.best_match and 'd' in args.best_match:
                    print(
                        "Warning: Destination language \"{dst}\" not supported. "
                        "Run with \"-lsc\"/\"--list-translation-codes\" "
                        "to see all supported languages.".format(dst=args.dst_language)
                    )
                    best_result = lang_code_utils.match_print(
                        dsr_lang=args.dst_language,
                        match_list=list(googletrans.constants.LANGUAGES.keys()),
                        min_score=args.min_score)
                    if best_result:
                        print("Use {lang_code} instead.".format(lang_code=best_result[0]))
                        args.dst_language = best_result[0]
                    else:
                        raise core.PrintAndStopException(
                            "Match failed. Still using {lang_code}. "
                            "Program stopped".format(
                                lang_code=args.dst_language))

                else:
                    raise core.PrintAndStopException(
                        "Error: Destination language \"{dst}\" not supported. "
                        "Run with \"-lsc\"/\"--list-translation-codes\" "
                        "to see all supported languages. "
                        "Or use \"-bm\"/\"--best-match\" to get a best match".format(
                            dst=args.dst_language)
                    )

        if args.dst_language == args.src_language:
            raise core.PrintAndStopException(
                "Error: Source language is the same as the Destination language. "
            )

    else:
        raise core.PrintAndStopException(
            "Error: Source language not provided. "
        )

    if args.styles == ' ':
        # when args.styles is used but without option
        # its value is ' '
        if not args.ext_regions:
            raise core.PrintAndStopException(
                "Error: External speech regions file not provided."
            )
        else:
            args.styles = args.ext_regions


def fix_args(args):
    """
    Check that the commandline arguments value passed to autosub are proper.
    """
    if not args.ext_regions:
        if args.min_region_size < constants.MIN_REGION_SIZE:
            print(
                "Your minimum region size {mrs0} is smaller than {mrs}.\n"
                "Now reset to {mrs}".format(mrs0=args.min_region_size,
                                            mrs=constants.MIN_REGION_SIZE)
            )
            args.min_region_size = constants.MIN_REGION_SIZE

        if args.max_region_size > constants.MAX_EXT_REGION_SIZE:
            print(
                "Your maximum region size {mrs0} is larger than {mrs}.\n"
                "Now reset to {mrs}".format(mrs0=args.max_region_size,
                                            mrs=constants.MAX_EXT_REGION_SIZE)
            )
            args.max_region_size = constants.MAX_EXT_REGION_SIZE

        if args.max_continuous_silence < 0:
            print(
                "Your maximum continuous silence {mxcs} is smaller than 0.\n"
                "Now reset to {dmxcs}".format(mxcs=args.max_continuous_silence,
                                              dmxcs=constants.DEFAULT_CONTINUOUS_SILENCE)
            )
            args.max_continuous_silence = constants.DEFAULT_CONTINUOUS_SILENCE


def get_timed_text(
        is_empty_dropped,
        regions,
        text_list
):
    """
    Get timed text list.
    """
    if is_empty_dropped:
        # drop empty regions
        timed_text = [(region, text) for region, text in zip(regions, text_list) if text]
    else:
        # keep empty regions
        timed_text = []
        i = 0
        length = len(regions)
        if length != len(text_list):
            raise core.PrintAndStopException(
                "Error: Regions and text_list don't have the same length."
            )
        while i < length:
            timed_text.append((regions[i], text_list[i]))
            i = i + 1

    return timed_text


def subs_trans(  # pylint: disable=too-many-branches, too-many-statements, too-many-locals
        args,
        input_m=input,
        fps=30.0,
        styles_list=None):
    """
    Give args and translate a subtitles file.
    """
    if not args.output_files:
        raise core.PrintAndStopException(
            "\nNo works done."
            " Check your \"-of\"/\"--output-files\" option."
        )

    src_sub = pysubs2.SSAFile.load(args.input)
    text_list = []

    if args.styles and \
            (args.format == 'ass' or
             args.format == 'ssa' or
             args.format == 'ass.json'):
        src_sub.styles = \
            {styles_list[i]: styles_list[i + 1] for i in range(0, len(styles_list), 2)}
        for event in src_sub.events:
            event.style = styles_list[0]
            text_list.append(event.text)
    else:
        styles_list = [src_sub.events[0].style, ]
        for event in src_sub.events:
            text_list.append(event.text)

    # text translation
    if args.gtransv2:
        # use gtransv2
        translated_text = core.list_to_gtv2(
            text_list=text_list,
            api_key=args.gtransv2,
            concurrency=args.trans_concurrency,
            src_language=args.src_language,
            dst_language=args.dst_language,
            lines_per_trans=args.lines_per_trans
        )
    else:
        # use googletrans
        translated_text = core.list_to_googletrans(
            text_list,
            src_language=args.src_language,
            dst_language=args.dst_language,
            sleep_seconds=args.sleep_seconds,
            user_agent=args.user_agent,
            service_urls=args.service_urls
        )

    try:
        args.output_files.remove("bilingual")
        bilingual_sub = pysubs2.SSAFile()
        bilingual_sub.styles = src_sub.styles
        bilingual_sub.events = src_sub.events.copy()
        if args.styles and \
                len(styles_list) == 2 and \
                (args.format == 'ass' or
                 args.format == 'ssa' or
                 args.format == 'ass.json'):
            sub_utils.pysubs2_ssa_event_add(
                src_ssafile=bilingual_sub,
                dst_ssafile=bilingual_sub,
                text_list=translated_text,
                style_name=styles_list[2])
        else:
            sub_utils.pysubs2_ssa_event_add(
                src_ssafile=bilingual_sub,
                dst_ssafile=bilingual_sub,
                text_list=translated_text,
                style_name=styles_list[0])
        # formatting timed_text to subtitles string
        bilingual_name = "{base}.{nt}.{extension}".format(base=args.output,
                                                          nt=args.src_language +
                                                          '&' + args.dst_language,
                                                          extension=args.format)
        if args.format != 'ass.json':
            bilingual_string = bilingual_sub.to_string(format_=args.format, fps=fps)
        else:
            bilingual_string = bilingual_sub.to_string(format_='json')

        if args.format == 'mpl2':
            extension = 'mpl2.txt'
        else:
            extension = args.format

        subtitles_file_path = core.str_to_file(
            str_=bilingual_string,
            output=bilingual_name,
            extension=extension,
            input_m=input_m
        )
        # subtitles string to file
        print("Bilingual subtitles file "
              "created at \"{}\"".format(subtitles_file_path))

        if not args.output_files:
            raise core.PrintAndStopException("\nAll works done.")

    except KeyError:
        pass

    try:
        args.output_files.remove("dst")
        dst_sub = pysubs2.SSAFile()
        dst_sub.styles = src_sub.styles
        # formatting timed_text to subtitles string
        if len(styles_list) == 2:
            sub_utils.pysubs2_ssa_event_add(
                src_ssafile=src_sub,
                dst_ssafile=dst_sub,
                text_list=translated_text,
                style_name=styles_list[2])
        else:
            sub_utils.pysubs2_ssa_event_add(
                src_ssafile=src_sub,
                dst_ssafile=dst_sub,
                text_list=translated_text,
                style_name=styles_list[0])
        # formatting timed_text to subtitles string
        dst_name = "{base}.{nt}.{extension}".format(base=args.output,
                                                    nt=args.dst_language,
                                                    extension=args.format)
        if args.format != 'ass.json':
            dst_string = dst_sub.to_string(format_=args.format, fps=fps)
        else:
            dst_string = dst_sub.to_string(format_='json')

        if args.format == 'mpl2':
            extension = 'mpl2.txt'
        else:
            extension = args.format

        subtitles_file_path = core.str_to_file(
            str_=dst_string,
            output=dst_name,
            extension=extension,
            input_m=input_m
        )
        # subtitles string to file
        print("Destination language subtitles "
              "file created at \"{}\"".format(subtitles_file_path))

    except KeyError:
        pass


def get_fps(
        args,
        input_m=input
):
    """
    Give args and get fps.
    """
    if args.format == 'sub':
        if not args.sub_fps:
            fps = ffmpeg_utils.ffprobe_get_fps(
                args.input,
                input_m=input_m)
            if fps == 0.0:
                if not args.yes:
                    args.format = 'srt'
                else:
                    raise pysubs2.exceptions.Pysubs2Error
        else:
            fps = args.sub_fps
    else:
        fps = 0.0

    return fps


def audio_or_video_prcs(  # pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-arguments
        args,
        input_m=input,
        fps=30.0,
        ffmpeg_cmd="ffmpeg",
        styles_list=None,
        is_flac=False):
    """
    Give args and process an input audio or video file.
    """

    if args.http_speech_to_text_api:
        gsv2_api_url = "http://" + constants.GOOGLE_SPEECH_V2_API_URL
    else:
        gsv2_api_url = "https://" + constants.GOOGLE_SPEECH_V2_API_URL

    if not args.output_files:
        raise core.PrintAndStopException(
            "\nNo works done."
            " Check your \"-of\"/\"--output-files\" option."
        )

    if args.ext_regions:
        # use external speech regions
        print("Use external speech regions.")
        regions = sub_utils.sub_to_speech_regions(
            source_file=args.input,
            ffmpeg_cmd=ffmpeg_cmd,
            sub_file=args.ext_regions
        )

    else:
        # use auditok_gen_speech_regions
        mode = 0
        if args.strict_min_length:
            mode = auditok.StreamTokenizer.STRICT_MIN_LENGTH
            if args.drop_trailing_silence:
                mode = mode | auditok.StreamTokenizer.DROP_TRAILING_SILENCE
        elif args.drop_trailing_silence:
            mode = auditok.StreamTokenizer.DROP_TRAILING_SILENCE

        regions = core.auditok_gen_speech_regions(
            source_file=args.input,
            ffmpeg_cmd=ffmpeg_cmd,
            energy_threshold=args.energy_threshold,
            min_region_size=constants.MIN_REGION_SIZE,
            max_region_size=constants.MAX_REGION_SIZE,
            max_continuous_silence=constants.DEFAULT_CONTINUOUS_SILENCE,
            mode=mode
        )

    if args.speech_language:
        # process output first
        try:
            args.output_files.remove("regions")
            if args.styles and \
                    (args.format == 'ass' or
                     args.format == 'ssa' or
                     args.format == 'ass.json'):
                times_string, extension = core.list_to_ass_str(
                    text_list=regions,
                    styles_list=styles_list,
                    subtitles_file_format=args.format
                )
            else:
                times_string, extension = core.list_to_sub_str(
                    timed_text=regions,
                    fps=fps,
                    subtitles_file_format=args.format
                )
            # times to subtitles string
            times_name = "{base}.{nt}.{extension}".format(base=args.output,
                                                          nt="times",
                                                          extension=args.format)
            subtitles_file_path = core.str_to_file(
                str_=times_string,
                output=times_name,
                extension=extension,
                input_m=input_m
            )
            # subtitles string to file

            print("Times file created at \"{}\"".format(subtitles_file_path))

            if not args.output_files:
                raise core.PrintAndStopException("\nAll works done.")

        except KeyError:
            pass

        # speech to text
        if not is_flac:
            audio_flac = ffmpeg_utils.source_to_audio(
                args.input,
                ffmpeg_cmd=ffmpeg_cmd,
                rate=44100,
                file_ext='.flac')
        else:
            audio_flac = args.input

        text_list = core.speech_to_text(
            audio_flac=audio_flac,
            ffmpeg_cmd=ffmpeg_cmd,
            api_url=gsv2_api_url,
            regions=regions,
            api_key=args.gspeechv2,
            concurrency=args.speech_concurrency,
            src_language=args.speech_language,
            min_confidence=args.min_confidence,
        )

        if not args.keep:
            os.remove(audio_flac)

        timed_text = get_timed_text(
            is_empty_dropped=args.drop_empty_regions,
            regions=regions,
            text_list=text_list
        )

        if args.dst_language:
            # process output first
            try:
                args.output_files.remove("src")
                if args.styles and \
                        (args.format == 'ass' or
                         args.format == 'ssa' or
                         args.format == 'ass.json'):
                    src_string, extension = core.list_to_ass_str(
                        text_list=timed_text,
                        styles_list=styles_list[:2],
                        subtitles_file_format=args.format,
                    )
                else:
                    src_string, extension = core.list_to_sub_str(
                        timed_text=timed_text,
                        fps=fps,
                        subtitles_file_format=args.format
                    )

                # formatting timed_text to subtitles string
                src_name = "{base}.{nt}.{extension}".format(base=args.output,
                                                            nt=args.speech_language,
                                                            extension=args.format)
                subtitles_file_path = core.str_to_file(
                    str_=src_string,
                    output=src_name,
                    extension=extension,
                    input_m=input_m
                )
                # subtitles string to file
                print("Speech language subtitles "
                      "file created at \"{}\"".format(subtitles_file_path))

                if not args.output_files:
                    raise core.PrintAndStopException("\nAll works done.")

            except KeyError:
                pass

            # text translation
            if args.gtransv2:
                # use gtransv2
                translated_text = core.list_to_gtv2(
                    text_list=text_list,
                    api_key=args.gtransv2,
                    concurrency=args.trans_concurrency,
                    src_language=args.src_language,
                    dst_language=args.dst_language,
                    lines_per_trans=args.lines_per_trans
                )
            else:
                # use googletrans
                translated_text = core.list_to_googletrans(
                    text_list,
                    src_language=args.src_language,
                    dst_language=args.dst_language,
                    sleep_seconds=args.sleep_seconds,
                    user_agent=args.user_agent,
                    service_urls=args.service_urls
                )

            timed_trans = get_timed_text(
                is_empty_dropped=args.drop_empty_regions,
                regions=regions,
                text_list=translated_text
            )

            try:
                args.output_files.remove("bilingual")
                if args.styles and \
                        (args.format == 'ass' or
                         args.format == 'ssa' or
                         args.format == 'ass.json'):
                    bilingual_string, extension = core.list_to_ass_str(
                        text_list=[timed_text, timed_trans],
                        styles_list=styles_list,
                        subtitles_file_format=args.format,
                    )
                else:
                    bilingual_string, extension = core.list_to_sub_str(
                        timed_text=timed_text + timed_trans,
                        fps=fps,
                        subtitles_file_format=args.format
                    )
                # formatting timed_text to subtitles string
                bilingual_name = "{base}.{nt}.{extension}".format(base=args.output,
                                                                  nt=args.src_language +
                                                                  '&' + args.dst_language,
                                                                  extension=args.format)
                subtitles_file_path = core.str_to_file(
                    str_=bilingual_string,
                    output=bilingual_name,
                    extension=extension,
                    input_m=input_m
                )
                # subtitles string to file
                print("Bilingual subtitles file "
                      "created at \"{}\"".format(subtitles_file_path))

                if not args.output_files:
                    raise core.PrintAndStopException("\nAll works done.")

            except KeyError:
                pass

            try:
                args.output_files.remove("dst")
                # formatting timed_text to subtitles string
                if args.styles and \
                        (args.format == 'ass' or
                         args.format == 'ssa' or
                         args.format == 'ass.json'):
                    if len(args.styles) == 4:
                        dst_string, extension = core.list_to_ass_str(
                            text_list=timed_trans,
                            styles_list=styles_list[2:4],
                            subtitles_file_format=args.format,
                        )
                    else:
                        dst_string, extension = core.list_to_ass_str(
                            text_list=timed_trans,
                            styles_list=styles_list,
                            subtitles_file_format=args.format,
                        )
                else:
                    dst_string, extension = core.list_to_sub_str(
                        timed_text=timed_trans,
                        fps=fps,
                        subtitles_file_format=args.format
                    )
                dst_name = "{base}.{nt}.{extension}".format(base=args.output,
                                                            nt=args.dst_language,
                                                            extension=args.format)
                subtitles_file_path = core.str_to_file(
                    str_=dst_string,
                    output=dst_name,
                    extension=extension,
                    input_m=input_m
                )
                # subtitles string to file
                print("Destination language subtitles "
                      "file created at \"{}\"".format(subtitles_file_path))

            except KeyError:
                pass

        else:
            if len(args.output_files) > 1 or not ({"dst", "src"} & args.output_files):
                print(
                    "Override \"-of\"/\"--output-files\" due to your args too few."
                    "\nOutput source subtitles file only."
                )
            timed_text = get_timed_text(
                is_empty_dropped=args.drop_empty_regions,
                regions=regions,
                text_list=text_list
            )
            if args.styles and \
                    (args.format == 'ass' or
                     args.format == 'ssa' or
                     args.format == 'ass.json'):
                src_string, extension = core.list_to_ass_str(
                    text_list=timed_text,
                    styles_list=styles_list,
                    subtitles_file_format=args.format,
                )
            else:
                src_string, extension = core.list_to_sub_str(
                    timed_text=timed_text,
                    fps=fps,
                    subtitles_file_format=args.format
                )
            # formatting timed_text to subtitles string
            src_name = "{base}.{nt}.{extension}".format(base=args.output,
                                                        nt=args.speech_language,
                                                        extension=args.format)
            subtitles_file_path = core.str_to_file(
                str_=src_string,
                output=src_name,
                extension=extension,
                input_m=input_m
            )
            # subtitles string to file
            print("Speech language subtitles "
                  "file created at \"{}\"".format(subtitles_file_path))

    else:
        print(
            "Override \"-of\"/\"--output-files\" due to your args too few."
            "\nOutput regions subtitles file only."
        )
        if args.styles and \
                (args.format == 'ass' or
                 args.format == 'ssa' or
                 args.format == 'ass.json'):
            times_subtitles, extension = core.list_to_ass_str(
                text_list=regions,
                styles_list=styles_list,
                subtitles_file_format=args.format
            )
        else:
            times_subtitles, extension = core.list_to_sub_str(
                timed_text=regions,
                fps=fps,
                subtitles_file_format=args.format
            )
        # times to subtitles string
        times_name = "{base}.{nt}.{extension}".format(base=args.output,
                                                      nt="times",
                                                      extension=args.format)
        subtitles_file_path = core.str_to_file(
            str_=times_subtitles,
            output=times_name,
            extension=extension,
            input_m=input_m
        )
        # subtitles string to file

        print("Times file created at \"{}\"".format(subtitles_file_path))
