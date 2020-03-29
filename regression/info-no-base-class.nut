class Regression
{
    function GetAuthor()      { return "Regression"; }
    function GetName()        { return "Regression"; }
    function GetDescription() { return "Regression"; }
    function GetVersion()     { return 1; }
    function GetDate()        { return "2020-02-02"; }
    function GetShortName()   { return "REGR"; }
    function CreateInstance() { return "Regression"; }
    function GetAPIVersion()  { return "1.0"; }
}

RegisterAI(Regression());
